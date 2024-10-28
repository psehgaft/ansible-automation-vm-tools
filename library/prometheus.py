# (c) 2018 xinau <felix.ehrenpfort@protonmail.com>
# GNU General Public License v3.0+ (see https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
  callback: prometheus
  callback_type: aggregate
  short_description: expose playbook stats to as Prometheus metrics.
  version_added: "2.8"
  description:
    - This callback exposes playbook statistics as Prometheus metrics.
    - Metrics can be gather using the node exporters textfile collector.
  options:
    output_file:
      name: Prometheus metrics output file
      default: /var/lib/prometheus/node_exporter/ansible.prom
      description: File to write Prometheus metrics to.
      env:
        - name: PROMETHEUS_OUTPUT_FILE
    fail_on_change:
      name: Consider task failed on change
      default: False
      description: Consider any tasks reporting "changed" as a failures
      env:
        - name: PROMETHEUS_FAIL_ON_CHANGE
    fail_on_ignore:
      name: Consider task failed on ignore
      default: False
      description: Consider failed tasks as a failures even if ignore_on_errors is set
      env:
        - name: PROMETHEUS_FAIL_ON_IGNORE
    include_setup_tasks:
      name: Include setup tasks in metrics
      default: True
      description: Should the setup tasks be included in the final report
      env:
        - name: PROMETHEUS_INCLUDE_SETUP_TASKS
  requirements:
    - whitelist in configuration
    - prometheus_client (python lib)
'''

import os
import sys
import time

from ansible import constants as C
from ansible.module_utils import ansible_release
from ansible.plugins.callback import CallbackBase

try:
    from prometheus_client import CollectorRegistry, Gauge, Info, write_to_textfile

    HAS_PROMETHEUS_CLIENT = True
except ImportError:
    HAS_PROMETHEUS_CLIENT = False


class CallbackModule(CallbackBase):
    """
    This callback exposes playbook statistics as Prometheus metrics.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'prometheus'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()

        self._output_file = os.getenv('PROMETHEUS_OUTPUT_FILE', '/var/lib/prometheus/node_exporter')
        self._fail_on_change = os.getenv('PROMETHEUS_FAIL_ON_CHANGE', 'False').lower()
        self._fail_on_ignore = os.getenv('PROMETHEUS_FAIL_ON_IGNORE', 'False').lower()
        self._include_setup_tasks = os.getenv('PROMETHEUS_INCLUDE_SETUP_TASKS', 'True').lower()

        self._play_name = None
        self._start_time = None
        self._task_data = {}

        self.disabled = False

        if not HAS_PROMETHEUS_CLIENT:
            self.disabled = True
            self._display.warning(
                'The `prometheus_client` python module is not installed. '
                'Disabling the `prometheus` callback plugin.'
            )
            return

        output_dir = os.path.dirname(self._output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self._registry = CollectorRegistry()
        self._register_metrics(self._registry)

    def _register_metrics(self, registry):
        """ register prometheus metrics """

        self._metric_info_ansible = Info(
            'ansible', 'Information on the ansible runtime environment',
            registry=registry
        ).info({
            'version': ansible_release.__version__,
            'python_version': "{}.{}.{}".format(
                sys.version_info.major, sys.version_info.minor, sys.version_info.micro
            ),
        })
        self._metric_info_playbook = Info(
            'ansible_playbook', 'Information on the ansible playbook being executed',
            registry=registry
        )
        self._metric_playbook_duration = Gauge(
            'ansible_playbook_duration_seconds', 'Time spend in seconds for ansible playbook to complete',
            registry=registry
        )
        self._metric_tasks_duration = Gauge(
            'ansible_tasks_duration_seconds', 'Time spend in seconds executing ansible play tasks',
            ['play', 'host'],
            registry=registry
        )
        self._metric_tasks_status = Gauge(
            'ansible_tasks_status', 'Cumulative number of task status of each ansible play',
            ['play', 'host', 'status'],
            registry=registry
        )

    def _start_playbook(self, playbook):
        """ record the start of playbook """

        path = playbook._file_name
        name = os.path.basename(path)

        self._metric_info_playbook.info({'name': name})
        self._start_time = time.time()

    def _finish_playbook(self):
        """ record the finish of playbook """

        finish_time = time.time()
        self._metric_playbook_duration.inc(int(finish_time - self._start_time))

    def _start_task(self, task):
        """ record the start of a task for one or more hosts """

        task_uuid = task._uuid
        if task_uuid in self._task_data:
            return

        self._task_data[task_uuid] = TaskData(self._play_name, task.action)

    def _finish_task(self, status, result):
        """ record the results of a task for a single host """

        task_uuid = result._task._uuid
        task_data = self._task_data[task_uuid]

        if task_data.action in C._ACTION_SETUP and self._include_setup_tasks == 'false':
            return

        changed = result._result.get('changed', False)
        host = result._host.name
        play = task_data.play

        if self._fail_on_change == 'true' and status == 'ok' and changed:
            status = 'failed'

        self._metric_tasks_status.labels(play, host, status).inc(1)
        if changed:
            self._metric_tasks_status.labels(play, host, 'changed').inc(1)

        finish_time = time.time()
        self._metric_tasks_duration.labels(play, host).inc(int(finish_time - task_data.start_time))

    def write_metrics_textfile(self):
        """ write prometheus metrics to textfile """

        write_to_textfile(self._output_file, self._registry)

    def v2_playbook_on_start(self, playbook):
        self._start_playbook(playbook)

    def v2_playbook_on_play_start(self, play):
        self._play_name = play.get_name()

    def v2_runner_on_no_hosts(self, task):
        self._start_task(task)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._start_task(task)

    def v2_playbook_on_cleanup_task_start(self, task):
        self._start_task(task)

    def v2_playbook_on_handler_task_start(self, task):
        self._start_task(task)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if ignore_errors and self._fail_on_ignore != 'true':
            self._finish_task('ok', result)
        else:
            self._finish_task('failed', result)

    def v2_runner_on_ok(self, result):
        self._finish_task('ok', result)

    def v2_runner_on_skipped(self, result):
        self._finish_task('skipped', result)

    def v2_playbook_on_stats(self, stats):
        self._finish_playbook()
        self.write_metrics_textfile()


class TaskData:
    """
    Data about an individual task.
    """

    def __init__(self, play, action):
        self.play = play
        self.action = action
        self.start_time = time.time()