"""Offline simulation: no model API, real device, or business data is used."""
from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass
class Request:
    message_id: str
    operation_id: str
    scenario: str
    authorized: bool = True
    supported: bool = True
    cancelled: bool = False

class Simulator:
    def __init__(self):
        self.operations = {}
        self.effect_count = 0
        self.traces = []

    def run(self, request):
        spans = []
        def finish(status, reply):
            result = {'status': status, 'reply': reply}
            self.traces.append({'message_id': request.message_id,
                'request_id': f'request-{len(self.traces)+1}',
                'trace_id': f'trace-{len(self.traces)+1}',
                'operation_id': request.operation_id, 'version': 'simulation-v0.1',
                'spans': spans, 'result': result})
            return result
        if not request.authorized:
            spans.append({'step': 'authorization', 'status': 'denied'})
            return finish('rejected', '没有操作权限，未发送指令。')
        if request.cancelled:
            spans.append({'step': 'cancellation', 'status': 'before_dispatch'})
            return finish('cancelled', '已取消，未发送指令。')
        if not request.supported:
            spans.append({'step': 'capability', 'status': 'unsupported'})
            return finish('unsupported', '设备不支持该功能，未发送指令。')
        if request.operation_id in self.operations:
            known = self.operations[request.operation_id]
            spans.append({'step': 'idempotency_lookup', 'status': known})
            # A pending/unknown write must not be repeated automatically.
            return finish(known, self.reply(known))
        if request.scenario not in {'success','failure','timeout_applied','timeout_unknown'}:
            return finish('rejected', '未知模拟场景，未发送指令。')
        self.operations[request.operation_id] = 'unknown'
        spans.append({'step': 'dispatch', 'status': 'sent'})
        if request.scenario == 'failure':
            status = 'failed'
            spans.append({'step': 'device_result', 'status': 'explicit_failure'})
        elif request.scenario == 'timeout_unknown':
            status = 'unknown'
            spans += [{'step': 'transport', 'status': 'timeout'},
                      {'step': 'status_query', 'status': 'unavailable'}]
        else:
            self.effect_count += 1
            status = 'succeeded'
            if request.scenario == 'timeout_applied':
                spans += [{'step': 'transport', 'status': 'timeout'},
                          {'step': 'status_query', 'status': 'succeeded'}]
            else:
                spans.append({'step': 'device_result', 'status': 'succeeded'})
        self.operations[request.operation_id] = status
        return finish(status, self.reply(status))

    @staticmethod
    def reply(status):
        return {'succeeded':'设备已确认开启。', 'failed':'设备明确返回执行失败。',
                'unknown':'暂未确认执行结果，未自动重复发送指令。'}[status]


def evaluate():
    scenarios = [
        ('正常成功', Request('m1','o1','success'), 'succeeded', 1),
        ('明确失败', Request('m2','o2','failure'), 'failed', 0),
        ('成功但回执超时', Request('m3','o3','timeout_applied'), 'succeeded', 1),
        ('超时且无法核对', Request('m4','o4','timeout_unknown'), 'unknown', 0),
        ('发送前取消', Request('m5','o5','success',cancelled=True), 'cancelled', 0),
        ('设备不支持', Request('m6','o6','success',supported=False), 'unsupported', 0),
        ('没有权限', Request('m7','o7','success',authorized=False), 'rejected', 0),
    ]
    results, traces = [], []
    for name, request, expected, effects in scenarios:
        system = Simulator()
        result = system.run(request)
        passed = result['status'] == expected and system.effect_count == effects
        results.append({'case':name,'expected':expected,'actual':result['status'],
                        'effects':system.effect_count,'passed':passed})
        traces.extend(system.traces)
    for scenario, expected, effects in [('success','succeeded',1),('timeout_unknown','unknown',0)]:
        system = Simulator()
        first = Request('m-repeat-1','shared-operation',scenario)
        second = Request('m-repeat-2','shared-operation',scenario)
        system.run(first)
        result = system.run(second)
        passed = result['status'] == expected and system.effect_count == effects and len(
            [s for t in system.traces for s in t['spans'] if s['step']=='dispatch']) == 1
        results.append({'case':f'重复请求-{scenario}','expected':expected,
                        'actual':result['status'],'effects':system.effect_count,'passed':passed})
        traces.extend(system.traces)
    # IDs are local to each simulation; prefix them before combining datasets.
    for i,t in enumerate(traces,1):
        t['trace_id'] = f'eval-trace-{i}'
        t['request_id'] = f'eval-request-{i}'
    out = Path(__file__).parent/'results'
    out.mkdir(exist_ok=True)
    report={'scope':'deterministic offline simulation; not an LLM or production benchmark',
            'passed':sum(r['passed'] for r in results),'total':len(results),'cases':results}
    (out/'evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not all(r['passed'] for r in results):
        raise SystemExit(1)

if __name__ == '__main__':
    evaluate()
