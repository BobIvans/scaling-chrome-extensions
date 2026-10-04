"""Versioned daily IANA schedules admitting registered jobs into canonical Core."""
from __future__ import annotations
from datetime import date, datetime, time as daytime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import time

import automation_core as core
import workflow_state as state

SCHEMA='occ.durable-schedule.v2'
FIELDS={'schema','schedule_id','revision','enabled','template','timezone','local_time',
        'start_date','end_date','gap_policy','fold_policy','catch_up','catch_up_limit'}


def validate(value):
    if not isinstance(value,dict) or set(value)!=FIELDS or value['schema']!=SCHEMA:
        raise ValueError('DURABLE_SCHEDULE_SCHEMA')
    core.identifier(value['schedule_id']);core.identifier(value['template'])
    state.integer(value['revision'],1);state.integer(value['catch_up_limit'],1)
    if type(value['enabled']) is not bool:
        raise ValueError('SCHEDULE_ENABLED_BOOLEAN')
    if value['gap_policy'] not in {'SKIP','SHIFT_FORWARD'} or value['fold_policy'] not in {'FIRST','SECOND','BOTH'} or value['catch_up'] not in {'SKIP','LATEST','BOUNDED'}:
        raise ValueError('DURABLE_SCHEDULE_POLICY')
    try:
        ZoneInfo(value['timezone'])
        t=daytime.fromisoformat(value['local_time'])
        if t.tzinfo is not None or len(value['local_time'])!=5:
            raise ValueError()
        start,end=date.fromisoformat(value['start_date']),date.fromisoformat(value['end_date'])
        if start>end:
            raise ValueError()
    except (ValueError,TypeError,ZoneInfoNotFoundError):
        raise ValueError('DURABLE_SCHEDULE_TIMEZONE_DATE_REQUIRED') from None
    return dict(value)


def resolve_slot(value, day):
    """Roundtrip validation distinguishes gap/fold; no host timezone assumptions."""
    z=ZoneInfo(value['timezone'])
    naive=datetime.combine(day,daytime.fromisoformat(value['local_time']))
    options=[]
    for fold in (0,1):
        aware=naive.replace(tzinfo=z,fold=fold)
        utc=aware.astimezone(timezone.utc)
        if utc.astimezone(z).replace(tzinfo=None)==naive and utc not in options:
            options.append(utc)
    options.sort()
    if not options and value['gap_policy']=='SHIFT_FORWARD':
        # Adding the offset gap preserves minutes (03:30 -> 04:30 in Riga).
        options=[naive.replace(tzinfo=z,fold=0).astimezone(timezone.utc)]
    if len(options)>1 and value['fold_policy']!='BOTH':
        options=[options[0] if value['fold_policy']=='FIRST' else options[-1]]
    return options


def tick(value, profile_path, *, apply=False, stop=False, now=None):
    value=validate(value)
    if type(apply) is not bool or type(stop) is not bool or apply and stop:
        raise ValueError('SCHEDULE_MODE')
    if not Path(profile_path).is_absolute():
        raise ValueError('SCHEDULE_ABSOLUTE_PROFILE_REQUIRED')
    now=time.time() if now is None else state.number(now)
    if not value['enabled'] and not stop:
        return {'state':'DISABLED','enqueued':False}
    if not apply and not stop:
        return {'state':'PREVIEW','enqueued':False,'worker_started':False,'schedule_revision':value['revision']}
    from native_adapter import operator_profile
    profile,policy=operator_profile(profile_path)
    payload=profile['templates'].get(value['template'])
    core.validate_job(payload,policy)
    definition={k:v for k,v in value.items() if k!='enabled'}
    binding=core.digest([definition,profile,policy])
    store=Path(profile['store']);key=value['schedule_id'];revision=value['revision']
    with state.transaction(store) as db:
        old=state.get(db,'schedule',key)
        if old:
            v=old['value']
            if revision<v['definition']['revision']:
                raise ValueError('DURABLE_SCHEDULE_STALE_REVISION')
            if revision==v['definition']['revision'] and binding!=v['binding']:
                # Rebind is explicit new schedule revision; do not dispatch drift.
                state.put(db,'schedule',key,{**v,'state':'PAUSED_BINDING_DRIFT'},old['revision'])
                return {'state':'PAUSED_BINDING_DRIFT','enqueued':False}
            if revision>v['definition']['revision']:
                if revision!=v['definition']['revision']+1:
                    raise ValueError('DURABLE_SCHEDULE_REVISION_SEQUENCE')
                for row in db.execute('SELECT job_id FROM workflow_occurrences WHERE schedule=? AND state=?',(key,'ADMITTED')):
                    db.execute("UPDATE jobs SET state='CANCELLED',cancel_requested=1 WHERE id=? AND state IN ('QUEUED','RETRY_READY')",(row[0],))
                old_value={'definition':value,'binding':binding,'cursor':v['cursor'],'state':'ACTIVE'}
            else:
                old_value=v
        else:
            initial=datetime.combine(date.fromisoformat(value['start_date']),daytime.min,ZoneInfo(value['timezone'])).timestamp()-1
            old_value={'definition':value,'binding':binding,'cursor':initial,'state':'ACTIVE'}
        expected=old['revision'] if old else 0
        if stop or old_value['state']=='STOPPED':
            state.put(db,'schedule',key,{**old_value,'state':'STOPPED'},expected)
            return {'state':'STOPPED_FUTURE_ADMISSIONS','enqueued':False}
        if old_value['state']!='ACTIVE':
            return {'state':old_value['state'],'enqueued':False}
        cursor=old_value['cursor']
        if now<cursor:
            return {'state':'CLOCK_MOVED_BACKWARD','enqueued':False}
        db.execute("UPDATE workflow_occurrences SET state='MISSED',reason=NULL WHERE schedule=? AND revision=? AND state='WAITING_CAPACITY'",(key,revision))
        z=ZoneInfo(value['timezone']);day=max(date.fromisoformat(value['start_date']),datetime.fromtimestamp(cursor,z).date())
        end=min(date.fromisoformat(value['end_date']),datetime.fromtimestamp(now,z).date())
        # Stream to ledger. Selection is done in SQL, no in-memory missed fanout.
        while day<=end:
            slots=resolve_slot(value,day)
            if not slots:
                gap_id=core.digest([key,revision,day.isoformat(),value['local_time'],'GAP'])
                if state.get(db,'schedule_gap',gap_id) is None:
                    state.put(db,'schedule_gap',gap_id,{'state':'SKIPPED_DST_GAP','schedule_id':key,'revision':revision,
                              'local_date':day.isoformat(),'local_time':value['local_time'],'timezone':value['timezone'],'policy':value['gap_policy']},0)
            for slot in slots:
                instant=slot.timestamp()
                if cursor<instant<=now:
                    occurrence=core.digest([key,revision,slot.isoformat(),day.isoformat()])
                    db.execute("INSERT OR IGNORE INTO workflow_occurrences VALUES (?,?,?,?,'MISSED',NULL,NULL)", (occurrence,key,revision,instant))
            day+=timedelta(days=1)
        if value['catch_up']=='LATEST':
            selected=db.execute("SELECT id FROM workflow_occurrences WHERE schedule=? AND revision=? AND state='MISSED' ORDER BY instant DESC LIMIT 1",(key,revision)).fetchall()
        elif value['catch_up']=='BOUNDED':
            selected=db.execute("SELECT id FROM workflow_occurrences WHERE schedule=? AND revision=? AND state='MISSED' ORDER BY instant LIMIT ?",(key,revision,value['catch_up_limit'])).fetchall()
        else:
            # SKIP admits an occurrence only during its own local minute.
            selected=db.execute("SELECT id FROM workflow_occurrences WHERE schedule=? AND revision=? AND state='MISSED' AND instant>? ORDER BY instant",(key,revision,now-60)).fetchall()
        admitted=[]
        for row in selected:
            try:
                job=core.enqueue_in_transaction(db,policy,'occ:'+row[0],payload)
            except ValueError as exc:
                if str(exc)!='QUEUE_CAPACITY_WAIT':
                    raise
                db.execute("UPDATE workflow_occurrences SET state='WAITING_CAPACITY',reason=? WHERE id=?",(str(exc),row[0]))
                continue
            db.execute("UPDATE workflow_occurrences SET state='ADMITTED',job_id=? WHERE id=?",(job['id'],row[0]));admitted.append(job['id'])
        db.execute("UPDATE workflow_occurrences SET state='SKIPPED',reason='CATCH_UP_POLICY' WHERE schedule=? AND revision=? AND state='MISSED'",(key,revision))
        state.put(db,'schedule',key,{**old_value,'cursor':now},expected)
        return {'state':'ADMITTED' if admitted else 'NO_NEW_OCCURRENCE','enqueued':bool(admitted),'job_ids':admitted,'worker_started':False}
