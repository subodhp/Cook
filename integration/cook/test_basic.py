import json
import requests
from retrying import retry
import time
import unittest
import uuid

class CookTest(unittest.TestCase):
    _multiprocess_can_split_ = True

    @retry(stop_max_delay=120000, wait_fixed=1000)
    def wait_for_job(self, job_id, status):
        job = self.session.get('%s/rawscheduler?job=%s' % (self.cook_url, job_id))
        self.assertEqual(200, job.status_code)
        job = job.json()[0]
        self.assertEqual(status, job['status'])
        return job

    def minimal_job(self, **kwargs):
        job = {
            'max_retries': 1,
            'mem': 100,
            'cpus': 1,
            'uuid': str(uuid.uuid4()),
            'command': 'echo hello',
            'name': 'echo',
            'priority': 1
        }
        job.update(kwargs)
        return job

    def setUp(self):
        self.cook_url = 'http://localhost:12321'
        self.session = requests.Session()

    def test_basic_submit(self):
        job_spec = self.minimal_job()
        request_body = {'jobs': [ job_spec ]}
        resp = self.session.post('%s/rawscheduler' % self.cook_url, json=request_body)
        self.assertEqual(resp.status_code, 201)
        job = self.wait_for_job(job_spec['uuid'], 'completed')
        self.assertEqual('success', job['instances'][0]['status'])

    def test_failing_submit(self):
        job_spec = self.minimal_job(command='exit 1')
        resp = self.session.post('%s/rawscheduler' % self.cook_url,
                                 json={'jobs': [job_spec]})
        self.assertEqual(201, resp.status_code)
        job = self.wait_for_job(job_spec['uuid'], 'completed')
        self.assertEqual(1, len(job['instances']))
        self.assertEqual('failed', job['instances'][0]['status'])

    # def test_failing_submit_with_retries(self):
    #     job_uuid = str(uuid.uuid4())
    #     print job_uuid
    #     jobspec = self.minimal_job(job_uuid)
    #     jobspec['command'] = 'exit 1'
    #     jobspec['max_retries'] = 3
    #     resp = self.session.post('%s/rawscheduler' % self.cook_url,
    #                              json={'jobs': [jobspec]})
    #     self.assertEqual(201, resp.status_code)
    #     job = self.wait_for_job(job_uuid, 'completed')
    #     self.assertEqual(3, len(job['instances']))
    #     for instance in job['instances']:
    #         self.assertEqual('failed', instance['status'])

    def test_max_runtime_exceeded(self):
        job_spec = self.minimal_job(command='sleep 60', max_runtime=5000)
        resp = self.session.post('%s/rawscheduler' % self.cook_url,
                                 json={'jobs': [job_spec]})
        self.assertEqual(201, resp.status_code)
        job = self.wait_for_job(job_spec['uuid'], 'completed')
        self.assertEqual(1, len(job['instances']))
        self.assertEqual('failed', job['instances'][0]['status'])

