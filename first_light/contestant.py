"""First Light V29 research: well-resolved concave turn confirmation.

Uses only injected motor observations. Exact raw integers determine the final
maximum and ties. Search decisions remain heuristic on unseen curves.
No hidden-score or first-place guarantee.
"""
from math import exp, log, sqrt
from statistics import median

_STAT_AMPLITUDE = float(1 << 20)

def _stat_values(raw):
    """Positive linear normalization; raw integer ordering remains external."""
    lo=min(raw); span=max(raw)-lo
    if span==0:return [0.0 for _ in raw]
    return [(v-lo)/span*_STAT_AMPLITUDE for v in raw]


DEFAULTS = {'stride': 12, 'min_stride': 6, 'scan_budget': 110,
            'minimum_lag': 24, 'safe_lag': 170, 'future_probability': .02,
            'credible_snr': 8, 'max_stride': 24,
            'background_ridge': .004, 'model_temperature': 1.0,
            'model_noise_floor': .012, 'fit_power': 16, 'variable_step': True,
            'refine_limit': 104, 'refine_sigma': 1.5, 'minimum_refine': 16,
            'noise_bonus': 2.0, 'center_grid': 24, 'stop_noise': 1.0}


def _shape(x, center, width, kind):
    t = (x-center)/width
    if kind == 0:
        return exp(-.5*t*t) if abs(t) < 35 else 0.0
    return 1.0/(1.0+t*t)


def _noise(positions, values):
    residual=[]
    for j in range(1,len(values)-1):
        dl=positions[j]-positions[j-1];dr=positions[j+1]-positions[j]
        if dl and dr and max(dl,dr) <= 3*min(dl,dr):
            residual.append(values[j]-(values[j-1]*dr+values[j+1]*dl)/(dl+dr))
    if len(residual) < 3:return 0.0
    center=median(residual)
    return 1.2*median(abs(v-center) for v in residual)


class _Posterior:
    def __init__(self, cfg):
        self.cfg=cfg
        grid=max(8,int(cfg['center_grid']))
        self.models=[[j/grid,w,k,0.,0.,0.,0.] for j in range(grid+1)
                     for w in [.012,.025,.05,.10,.20,.40] for k in [0,1]]
        self.xs=[];self.ys=[]
        self.sumx=self.sumxx=self.sumy=self.sumyy=self.sumxy=0.
        self.first=None;self.unit=0

    def add(self, x, raw):
        if self.first is None:self.first=raw
        delta=raw-self.first
        unit=max(self.unit,abs(delta))
        if unit!=self.unit:
            factor=self.unit/unit
            self.ys=[y*factor for y in self.ys]
            self.sumy*=factor;self.sumyy*=factor*factor;self.sumxy*=factor
            for m in self.models:m[6]*=factor
            self.unit=unit
        y=delta/unit*_STAT_AMPLITUDE if unit else 0.
        self.xs.append(x);self.ys.append(y)
        self.sumx+=x;self.sumxx+=x*x;self.sumy+=y;self.sumyy+=y*y;self.sumxy+=x*y
        for m in self.models:
            g=_shape(x,*m[:3]);m[3]+=g;m[4]+=g*g;m[5]+=x*g;m[6]+=y*g

    def infer(self, best_x):
        n=len(self.xs);mx=self.sumx/n;my=self.sumy/n
        vx=max(0.,self.sumxx-self.sumx*mx)
        vy=max(0.,self.sumyy-self.sumy*my)
        xy=self.sumxy-self.sumx*my
        ridge=self.cfg['background_ridge']*n
        span=max(self.ys)-min(self.ys)
        noise=_noise(self.xs[-15:],self.ys[-15:])
        floor=n*max(1.,noise,self.cfg['model_noise_floor']*span)**2
        fits=[]
        # Add localized hypotheses centered at the actual observed high point.
        local=[]
        for w in [.006,.012,.025,.05,.10,.20]:
            for kind in [0,1]:
                gs=[_shape(x,best_x,w,kind) for x in self.xs]
                local.append([best_x,w,kind,sum(gs),sum(g*g for g in gs),
                              sum(x*g for x,g in zip(self.xs,gs)),
                              sum(y*g for y,g in zip(self.ys,gs))])
        for center,width,kind,sg,sgg,sxg,syg in self.models+local:
            mg=sg/n;vg=max(0.,sgg-sg*mg);xg=sxg-self.sumx*mg;yg=syg-self.sumy*mg
            determinant=(vx+ridge)*vg-xg*xg
            if determinant<=max(1e-15,1e-12*vg):continue
            a=((vx+ridge)*yg-xg*xy)/determinant
            if a<0:
                a=0.;slope=xy/max(1e-15,vx+ridge)
            else:slope=(xy*vg-yg*xg)/determinant
            intercept=my-slope*mx-a*mg
            residual=max(0.,vy-2*a*yg-2*slope*xy+a*a*vg+2*a*slope*xg+slope*slope*vx)+ridge*slope*slope
            # A positive hill plus linear drift can attain its maximum at a
            # shifted summit or either endpoint. A small deterministic grid
            # avoids assuming that the hill's center itself is the maximum.
            test_x=[0.,1.,center]
            test_x.extend(max(0.,min(1.,center+t*width)) for t in [-2,-1,-.5,.5,1,2])
            px=max(test_x,key=lambda x:intercept+slope*x+a*_shape(x,center,width,kind))
            fits.append((residual,px,center,width,kind,intercept,slope,a))
        if not fits:return None
        minimum=min(f[0] for f in fits)
        power=min(n-3,self.cfg['fit_power'])/(2*self.cfg['model_temperature'])
        weights=[exp(-power*log((f[0]+floor)/(minimum+floor))) for f in fits]
        total=sum(weights)
        future=sum(w for w,f in zip(weights,fits) if f[1]>self.xs[-1]+.008)/total
        xp=sorted((f[1],w) for f,w in zip(fits,weights))
        cumulative=0.;median_x=xp[-1][0]
        for x,w in xp:
            cumulative+=w
            if cumulative>=total/2:median_x=x;break
        smooth=[median(self.ys[max(0,j-1):j+2]) for j in range(1,n-1)]
        coherent_snr=(max(smooth)-min(smooth))/max(1.,noise) if smooth else 0.
        return dict(future=future,median=median_x,noise=noise,coherent_snr=coherent_snr,
                    fit_error=sqrt(minimum/n)/max(1.,span),
                    snr=sum(w*f[7] for w,f in zip(weights,fits))/total/max(1.,noise,sqrt(minimum/n)),
                    width=sum(w*f[3] for w,f in zip(weights,fits))/total)


def _allow_stop(cfg, positions, y, fit, features):
    mode=cfg['guard_mode']
    if mode=='none':return True
    # An observed hill must have an actual decline, not just posterior mass.
    # The relative threshold is invariant to an additive focus-metric offset.
    if mode in ('decline','decline_support','combined'):
        if not features['emergency'] and (features['drop_fraction']<.10 or features['drop_noise']<2.):
            return False
    if mode in ('decline_support','combined'):
        # A peak forecast based on a handful of samples cannot estimate noise
        # robustly; require twelve observations and a width-scaled descent.
        if features['calls']<12:return False
        if not features['emergency'] and features['lag']<min(96.,.5*fit['width']*cfg['_length']):
            return False
    if mode in ('correlation','combined'):
        # Adjacent curvature can understate slowly correlated disturbances.
        # Compare the recent three-point second difference at two grid scales;
        # use the larger noise estimate rather than trusting a smooth wiggle.
        coarse_positions=positions[-21:][::2]
        coarse_values=y[-21:][::2]
        multi_noise=max(1.,fit['noise'],_noise(coarse_positions,coarse_values))
        smooth=[median(y[max(0,j-1):j+2]) for j in range(1,len(y)-1)]
        if smooth and max(smooth)-min(smooth)<8.*multi_noise:return False
    return True



def _confirm_symmetric_turn(positions, raw, best):
    """A local concave summit with observed, well-resolved descending flank.

    This is a shape test, not a global-maximum certificate. All statistics
    are translated and rescaled before arithmetic; final ordering stays exact.
    """
    n=len(positions)
    if n<9:return None
    bj=positions.index(best)
    if bj<4 or n-bj-1<3:return None
    if positions[-1]-best<18:return None
    y=_stat_values(raw)
    span=max(y)-min(y)
    if not span:return None
    drop=y[bj]-median(y[-3:])
    rise=y[bj]-median(y[:3])
    if rise<.65*span:return None
    # Fit the three observations on each side and the sampled high point.
    # No assumed peak amplitude, raw pedestal, or sensor measurement units.
    ids=list(range(bj-3,bj+4))
    unit=positions[ids[-1]]-positions[ids[0]]
    xs=[(positions[j]-best)/unit for j in ids]
    ys=[y[j]/span for j in ids]
    sums=[sum(x**k for x in xs) for k in range(5)]
    rhs=[sum(v*x**k for x,v in zip(xs,ys)) for k in range(3)]
    a=[[sums[j+k] for k in range(3)]+[rhs[j]] for j in range(3)]
    for k in range(3):
        pivot=max(range(k,3),key=lambda j:abs(a[j][k]))
        a[k],a[pivot]=a[pivot],a[k]
        if abs(a[k][k])<1e-12:return None
        q=a[k][k];a[k]=[v/q for v in a[k]]
        for j in range(3):
            if j==k:continue
            q=a[j][k];a[j]=[v-q*w for v,w in zip(a[j],a[k])]
    intercept,slope,curve=[a[j][3] for j in range(3)]
    if curve>=0:return None
    vertex=-slope/(2*curve)
    if not (xs[2]<vertex<xs[4]):return None
    residual=sqrt(sum((v-intercept-slope*x-curve*x*x)**2 for x,v in zip(xs,ys))/7)
    local_span=max(ys)-min(ys)
    noise=max(residual*sqrt(7./4.)*span,1.)
    if drop<8*noise or rise<24*noise:return None
    # All three rising and descending increments must point the right way;
    # curvature residuals alone can understate correlated interference.
    if any(y[j+1]<=y[j] for j in range(bj-3,bj)):return None
    if any(y[j+1]>=y[j] for j in range(bj,bj+3)):return None
    if y[-1]>y[-2]+noise:return None
    return dict(position=positions[-1],best=best,calls=n,drop=drop/span,
                rise=rise/span,residual=residual,noise=noise/span,
                fitted_peak=best+vertex*unit)


def _confirm_turn(positions, raw, best):
    existing=_confirm_symmetric_turn(positions,raw,best)
    if existing is not None:return existing
    n=len(positions)
    if n<9:return None
    bj=positions.index(best)
    if bj<4 or n-bj-1<3:return None
    if positions[-1]-best<18:return None
    y=_stat_values(raw)
    span=max(y)-min(y)
    if not span:return None
    rise=y[bj]-median(y[:3]);drop=y[bj]-median(y[-3:])
    if rise<.65*span:return None
    if any(y[j+1]<=y[j] for j in range(bj-3,bj)):return None
    if any(y[j+1]>=y[j] for j in range(bj,bj+3)):return None
    ids=list(range(bj-3,bj+4))
    unit=positions[ids[-1]]-positions[ids[0]]
    xs=[(positions[j]-best)/unit for j in ids]
    ys=[y[j]/span for j in ids]
    # The two flanks share their value and derivative at the sampled high
    # point, but may have different curvature. Four fitted coefficients and
    # seven observations leave three residual degrees of freedom.
    design=[[1.,x,x*x if x<0 else 0.,x*x if x>0 else 0.] for x in xs]
    a=[[sum(r[i]*r[j] for r in design) for j in range(4)]+
       [sum(r[i]*v for r,v in zip(design,ys))] for i in range(4)]
    for k in range(4):
        pivot=max(range(k,4),key=lambda j:abs(a[j][k]))
        a[k],a[pivot]=a[pivot],a[k]
        if abs(a[k][k])<1e-12:return None
        q=a[k][k];a[k]=[v/q for v in a[k]]
        for j in range(4):
            if j==k:continue
            q=a[j][k];a[j]=[v-q*w for v,w in zip(a[j],a[k])]
    intercept,slope,left,right=[a[j][4] for j in range(4)]
    if left>=0 or right>=0:return None
    vl=-slope/(2*left);vr=-slope/(2*right)
    if not (xs[2]<vl<xs[4] and xs[2]<vr<xs[4]):return None
    params=[intercept,slope,left,right]
    residual=sqrt(sum((v-sum(t*p for t,p in zip(row,params)))**2
                      for row,v in zip(design,ys))/7)
    noise=max(residual*sqrt(7./3.)*span,1.)
    if drop<8*noise or rise<24*noise:return None
    if y[-1]>y[-2]+noise:return None
    vertex=vl if slope<0 else vr
    return dict(position=positions[-1],best=best,calls=n,drop=drop/span,
                rise=rise/span,residual=residual,noise=noise/span,
                fitted_peak=best+vertex*unit,mechanism='asymmetric_shared_slope')

def _first_pass(length, run_motor, config=None):
    cfg=dict(DEFAULTS);cfg.update({'guard_mode': 'none','_length': length})
    if config:cfg.update(config)
    seen={};samples=[];position=0;best=None;calls=0
    posterior=_Posterior(cfg)
    def key(i):return seen[i],-abs(2*i-(length-1)),-i
    def read(i,scan=False):
        nonlocal position,best,calls
        if calls>=199:raise RuntimeError('query budget exhausted')
        value=run_motor(i);seen[i]=value;position=i;calls+=1
        if best is None or key(i)>key(best):best=i
        if scan:samples.append(i);posterior.add(i/max(1,length-1),value)
        return value
    if length<=180:
        for i in range(length):read(i)
        if position!=best:read(best)
        return best
    budget=max(30,min(135,int(cfg['scan_budget'])))
    read(0,True);fit=None
    rebound_cap=None;rebound_record=None;rebound_used=False
    flat_trigger=(length-1)//2+24
    # The old final park is either midpoint or the current sampled best if
    # the final midpoint read is lower. At activation we cap relative to
    # both possibilities, including their three-position target tolerance.
    flat_cap=min(length-1,(length-1)//2+196)
    flat_active=False;flat_started=False
    flat_record=None;flat_old_best=None
    while position<length-1 and calls<budget:
        step=int(cfg['stride'])
        if cfg['variable_step'] and fit is not None:
            distance=fit['median']*(length-1)-position
            step=max(int(cfg['min_stride']),min(cfg['max_stride'],int(max(0,distance)/4)))
        if rebound_cap is not None:step=12
        if flat_active:step=6
        step=max(step,(length-1-position+budget-calls-1)//max(1,budget-calls))
        next_position=min(length-1,position+step)
        if rebound_cap is not None:next_position=min(next_position,rebound_cap)
        if flat_active:next_position=min(next_position,flat_cap)
        read(next_position,True)
        if flat_active:
            events=cfg.get('_flat_events')
            if seen[best]>flat_record:
                # The old solution could score only if its actual target was
                # within three positions of midpoint or the frozen pre-flat
                # best. Check both windows before abandoning the safe cap.
                frontier=position;new_record=seen[best]
                middle=(length-1)//2
                windows=sorted({i for center in (middle,flat_old_best)
                                for i in range(max(0,center-3),min(length,center+4))},reverse=True)
                missing=[i for i in windows if i not in seen]
                # At most135 scanning calls and14 certificate reads, plus
                # return/park, fit strictly inside the199-call contract.
                # Keep an explicit guard for future changes to those bounds.
                if calls+len(missing)+2>199:
                    if events is not None:events.append(dict(event='flat_certificate_budget_stop',position=frontier))
                    if position!=best:read(best)
                    return best
                for i in missing:read(i)
                window_best=max(windows,key=key)
                if seen[window_best]>=new_record:
                    if events is not None:events.append(dict(event='flat_window_retained',position=frontier,window_best=window_best,certificate_reads=len(missing)))
                    if position!=best:read(best)
                    return best
                if events is not None:events.append(dict(event='flat_old_positive_excluded',position=frontier,certificate_reads=len(missing)))
                # Restoring the virtual forward frontier keeps scan samples
                # sorted. Cached observations can omit this physical revisit.
                if position!=frontier:read(frontier)
                flat_active=False
            elif position>=flat_cap:
                if events is not None:events.append(dict(event='bounded_flat_stop',position=position,cap=flat_cap))
                break
            else:
                # A lower value does not invalidate the previously observed
                # flat maximum. Keep its cap instead of releasing the scan.
                continue
        if rebound_cap is not None:
            if seen[best]>rebound_record:
                events=cfg.get('_scan_events')
                if events is not None:events.append(dict(event='new_record',position=position,best=best))
                rebound_cap=None
            elif position>=rebound_cap:
                events=cfg.get('_scan_events')
                if events is not None:events.append(dict(event='bounded_stop',position=position,best=best))
                break
        if calls<6:continue
        if rebound_cap is None and not flat_active:
            turn=_confirm_turn(samples,[seen[i] for i in samples],best)
            if turn is not None:
                events=cfg.get('_confirm_events')
                if events is not None:events.append(turn)
                break
        if max(seen.values())==min(seen.values()):
            if position>=flat_trigger:
                flat_active=True
                flat_record=seen[best]
                flat_old_best=best
                flat_cap=min(flat_cap,best+196)
                events=cfg.get('_flat_events')
                if not flat_started:
                    flat_started=True
                    if events is not None:events.append(dict(event='flat_extension',position=position,cap=flat_cap,old_sampled_best=best))
                if position>=flat_cap:
                    if events is not None:events.append(dict(event='bounded_flat_stop',position=position,cap=flat_cap))
                    break
            continue
        if calls%2==0 or position-best>=cfg['safe_lag']:
            fit=posterior.infer(best/max(1,length-1))
        if fit is None:continue
        lag=position-best
        y=posterior.ys
        drop=max(y)-median(y[-3:])
        future_limit=cfg['future_probability']
        credible = fit['coherent_snr'] >= cfg['credible_snr']
        proposed = credible and lag>=cfg['minimum_lag'] and fit['future']<future_limit and drop>max(1.,cfg['stop_noise']*fit['noise'])
        emergency = credible and lag>=cfg['safe_lag'] and fit['future']<.5 and drop>max(1.,fit['noise'])
        if proposed or emergency:
            span=max(y)-min(y)
            features = dict(position=position, best=best, calls=calls, lag=lag,
                            span=span, drop=drop, drop_fraction=drop/max(1.,span),
                            drop_noise=drop/max(1.,fit['noise']), emergency=bool(emergency),
                            **fit)
            hook=cfg.get('_decision_trace')
            if hook is not None:hook(features)
            if _allow_stop(cfg, samples, y, fit, features):
                if rebound_cap is not None:continue
                if not rebound_used and len(y)>=12:
                    bj=samples.index(best)
                    tail_noise=max(1.,fit['noise'],_noise(samples[-21:][::2],y[-21:][::2]))
                    recent=median(y[-3:])
                    valley_centers=range(max(bj+2,len(y)-10),len(y)-3)
                    valley=min((median(y[j-1:j+2]) for j in valley_centers),default=recent)
                    rising=median(y[-2:])>median(y[-4:-2])+tail_noise
                    rebound=recent-valley
                    cap=min(length-1,position+72,best+192)
                    if cap-position>=12 and rising and rebound>max(2.5*tail_noise,.04*span):
                        rebound_used=True;rebound_cap=cap;rebound_record=seen[best]
                        events=cfg.get('_scan_events')
                        if events is not None:events.append(dict(event='observed_rebound',position=position,best=best,cap=cap,rebound=rebound,noise=tail_noise,span=span))
                        continue
                break
    if flat_active or max(seen.values())==min(seen.values()):
        middle=(length-1)//2
        if middle not in seen:read(middle)
        if position!=best:read(best)
        return best
    # Refine all competitive intervals using the observed curvature and local
    # noise, traversing the selected indices in one descending motor pass.
    y=_stat_values([seen[i] for i in samples])
    bj=samples.index(best)
    noise=_noise(samples[max(0,bj-6):bj+7],y[max(0,bj-6):bj+7])
    candidates=[]
    for j in range(len(samples)-1):
        left,right=samples[j:j+2];yl,yr=y[j:j+2];gap=right-left
        ls=(yl-y[j-1])/(left-samples[j-1]) if j else 0.
        rs=(y[j+2]-yr)/(samples[j+2]-right) if j+2<len(samples) else 0.
        curv=max(0.,ls-rs)*gap/8
        for i in range(left+1,right):
            t=(i-left)/gap
            estimate=yl*(1-t)+yr*t+4*t*(1-t)*(curv+cfg['noise_bonus']*noise)
            candidates.append((estimate,-abs(i-best),-abs(2*i-(length-1)),i))
    competitive=sum(c[0]>=max(y)-cfg['refine_sigma']*noise for c in candidates)
    count=min(198-calls,int(cfg['refine_limit']),max(int(cfg['minimum_refine']),competitive))
    plan=sorted([c[-1] for c in sorted(candidates,reverse=True)[:count]],reverse=True)
    # A positive score must park at p >= R-202. Querying any q <= R-203
    # cannot provide that winning park. Remove these fixed-plan reads only if
    # the original first pass cannot subsequently perform certified recovery:
    # either no motor domain remains, or fewer than 34 virtual calls remain.
    terminal=position==length-1 or calls+len(plan)>=166
    retained=[i for i in plan if not terminal or i>position-203]
    prune_trace=cfg.get('_prune_trace')
    if prune_trace is not None:
        prune_trace.append(dict(phase='first',rightmost=position,calls=calls,
                                terminal=terminal,original=plan,retained=retained,
                                removed=[i for i in plan if i not in retained]))
    for i in retained:read(i)
    if position!=best:read(best)
    return best


def _virtual_solve(length, run_motor, config=None):
    """Preserve V17, then search further only after its final score is surely zero.

    If R-p>=203, every target within three of p has R-target>=200;
    all other targets fail the distance rule. This gate needs no target truth.
    """
    cfg=dict(config or {})
    seen={};calls=0;position=0;rightmost=0;direction=0;reversals=0;best=None
    def key(i):return seen[i],-abs(2*i-(length-1)),-i
    def read(i):
        nonlocal calls,position,rightmost,direction,reversals,best
        if calls>=199:raise RuntimeError('query budget exhausted')
        delta=i-position
        new_direction=(delta>0)-(delta<0)
        if new_direction and direction and new_direction!=direction:
            reversals+=1
        if reversals>6:raise RuntimeError('reversal budget exhausted')
        value=run_motor(i)
        seen[i]=value;calls+=1;position=i;rightmost=max(rightmost,i)
        if new_direction:direction=new_direction
        if best is None or key(i)>key(best):best=i
        return value
    result=_first_pass(length,read,cfg)
    remaining=199-calls
    needed_reversals=2+int(direction<0)
    certified=rightmost-position>=203
    eligible=certified and rightmost<length-1 and remaining>=34 and reversals+needed_reversals<=6
    trace=cfg.get('_recovery_trace')
    if trace is not None:
        trace.append(dict(certified=certified,eligible=eligible,calls=calls,
                          remaining=remaining,position=position,rightmost=rightmost,
                          reversals=reversals,first_best=best))
    if not eligible:return result
    # One fixed budget rule: reserve 25-40 fine observations and one final park.
    # Cover the remaining motor domain with the other observations, stopping
    # earlier only after a new global record and an observed descending flank.
    original_rightmost=rightmost
    original_best=best
    fine_reserve=min(40,max(25,remaining//3))
    scan_limit=calls+remaining-fine_reserve-1
    samples=[original_rightmost]
    read(original_rightmost+1);samples.append(position)
    while position<length-1 and calls<scan_limit:
        slots=scan_limit-calls
        step=max(12,(length-1-position+slots-1)//slots)
        read(min(length-1,position+step));samples.append(position)
        if len(samples)<5 or best<=original_rightmost:continue
        y=_stat_values([seen[x] for x in samples])
        noise=_noise(samples[-13:],y[-13:])
        spread=max(y)-min(y)
        lag=position-best
        drop=max(y)-median(y[-3:])
        if (lag>=max(24,step) and drop>max(1.,.10*spread,2.2*noise)
                and y[-1]<=y[-3]+max(1.,2.*noise)):
            break
    # Same curvature ranking as V17 on the new range, with the actual remaining
    # budget. All search queries are strictly beyond the old rightmost visit.
    y=_stat_values([seen[x] for x in samples])
    coarse_best=max(range(len(samples)),key=lambda j:key(samples[j]))
    noise=_noise(samples[max(0,coarse_best-6):coarse_best+7],y[max(0,coarse_best-6):coarse_best+7])
    candidates=[]
    for j in range(len(samples)-1):
        left,right=samples[j:j+2];yl,yr=y[j:j+2];gap=right-left
        ls=(yl-y[j-1])/(left-samples[j-1]) if j else 0.
        rs=(y[j+2]-yr)/(samples[j+2]-right) if j+2<len(samples) else 0.
        curv=max(0.,ls-rs)*gap/8
        for i in range(left+1,right):
            if i in seen or i<=original_rightmost:continue
            t=(i-left)/gap
            estimate=yl*(1-t)+yr*t+4*t*(1-t)*(curv+2.*noise)
            candidates.append((estimate,-abs(i-samples[coarse_best]),-abs(2*i-(length-1)),-i,i))
    count=min(198-calls,len(candidates))
    plan=sorted((c[-1] for c in sorted(candidates,reverse=True)[:count]),reverse=True)
    # This is the final refinement phase: no later recovery depends on its
    # observations. Delete only positions that cannot be a positive-score park.
    retained=[i for i in plan if i>rightmost-203]
    prune_trace=cfg.get('_prune_trace')
    if prune_trace is not None:
        prune_trace.append(dict(phase='recovery',rightmost=rightmost,calls=calls,
                                terminal=True,original=plan,retained=retained,
                                removed=[i for i in plan if i not in retained]))
    for i in retained:read(i)
    if position!=best:read(best)
    if trace is not None:
        trace.append(dict(completed=True,calls=calls,position=position,rightmost=rightmost,
                          reversals=reversals,first_best=original_best,final_best=best))
    return best


def _solve(length, run_motor, config=None):
    """Reuse static observations; defer redundant moves until final parking.

    The inner policy retains its original virtual call and movement accounting.
    Actual motor visits form a subsequence of that trace, including its final
    position, so this compression cannot add queries, distance, or reversals.
    """
    observed={};physical=None
    def cached_read(index):
        nonlocal physical
        if index in observed:return observed[index]
        value=run_motor(index)
        observed[index]=value;physical=index
        return value
    target=_virtual_solve(length,cached_read,config)
    if physical!=target:run_motor(target)
    return target


SUBMISSION_CONFIG = {'guard_mode': 'combined'}

def find_peak(array_length):
    _solve(array_length, run_motor, SUBMISSION_CONFIG)
    return 0
