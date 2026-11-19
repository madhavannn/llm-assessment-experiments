import random, json, pathlib, collections, zipfile
rng = random.Random(42)
OUT = pathlib.Path('task1_dataset')
OUT.mkdir(exist_ok=True)
# Keep test vocabulary and phrasing separate from training.
train_templates = {
 'create':['Add {task} to my to-do list','Create a task for {task}','Make a new task for {task}'],
 'schedule':['Schedule {task}','Arrange {task}','Book {task}'],
 'remind':['Remind me about {task}','Set a reminder for {task}','Create a reminder for {task}'],
 'cancel':['Cancel {task}','Remove {task} from my schedule','Delete the task for {task}'],
 'complete':['Mark {task} as done','Mark {task} as completed','Set the status of {task} to finished']}
test_templates = {
 'create':['Put {task} on my checklist','I need a new to-do item for {task}'],
 'schedule':['Please reserve a slot for {task}','Can you pencil in {task}?'],
 'remind':['Do not let me forget {task}','Give me a nudge about {task}'],
 'cancel':['Take {task} off my calendar','Call off {task}'],
 'complete':['I finished {task}; check it off','Tick off {task} as finished']}
train_tasks = ['team meeting','project review','dentist appointment','grocery shopping','coding assignment','job interview','gym session','email follow-up','budget review','car service','language lesson','website update','library visit','flight booking','weekly report','birthday planning','laundry','presentation practice','software installation','garden maintenance']
test_tasks = ['passport renewal','piano recital','garage cleanup','design workshop','plant watering','museum visit','science exhibition','bike repair','neighborhood cleanup','photography session']
dates = [None,'today','tomorrow','Monday','Tuesday','Friday']
times = [None,'09:00','10:00','11:30','14:00','17:00']
priorities = ['normal','low','high']
def generate(action, test=False):
    task = rng.choice(test_tasks if test else train_tasks)
    date = rng.choice(dates)
    time = rng.choice(times)
    priority = rng.choice(priorities)
    text = rng.choice((test_templates if test else train_templates)[action]).format(task=task).rstrip('?.')
    if test:
        when = []
        if date: when.append(date)
        if time:
            h,m = map(int,time.split(':'))
            when.append(f'at {h%12 or 12}:{m:02d} '+('AM' if h<12 else 'PM'))
        if when: text += ' — '+ ' '.join(when)
        text += '.' + {'normal':'','low':' No rush.','high':' Top priority.'}[priority]
    else:
        if date: text += ' on '+date if date not in ('today','tomorrow') else ' '+date
        if time: text += ' at '+time
        text += '.' + {'normal':'','low':' Low priority.','high':' This is urgent.'}[priority]
    return {'input':text,'output':{'action':action,'task':task,'date':date,'time':time,'priority':priority}}
def build(per_action,test=False):
    rows=[]; seen=set()
    for action in train_templates:
        count=0
        while count<per_action:
            row=generate(action,test)
            if row['input'] not in seen:
                seen.add(row['input']); rows.append(row); count+=1
    rng.shuffle(rows)
    return rows
pool=build(210)
train=[]; validation=[]
for action in train_templates:
    rows=[r for r in pool if r['output']['action']==action]
    train.extend(rows[:200]); validation.extend(rows[200:])
rng.shuffle(train); rng.shuffle(validation)
test=build(20,True)
splits={'train':train,'validation':validation,'test':test}
seen=set()
for name,rows in splits.items():
    assert len(rows)=={'train':1000,'validation':50,'test':100}[name]
    for row in rows:
        assert row['input'] not in seen
        seen.add(row['input'])
        assert set(row['output'])=={'action','task','date','time','priority'}
        assert row['output']['action'] in train_templates
    with (OUT/f'{name}.jsonl').open('w',encoding='utf-8') as f:
        for row in rows: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    print(name,len(rows),dict(collections.Counter(r['output']['action'] for r in rows)))
assert not ({r['output']['task'] for r in train+validation}&{r['output']['task'] for r in test})
print('Passed size, schema, duplicate and task-vocabulary checks.')
for row in test[:5]: print(json.dumps(row,ensure_ascii=False,indent=2))
