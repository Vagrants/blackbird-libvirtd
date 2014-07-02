# -*- encoding: utf-8 -*-
# pylint: disable=C0111,C0301,R0903

__VERSION__ = '0.1.0'

import re
import libvirt
import subprocess

from blackbird.plugins import base


class ConcreteJob(base.JobBase):
    """
    This class is Called by "Executor".
    Get vm instance information from libvirtd api,
    and send to specified zabbix server.
    """

    def __init__(self, options, queue=None, logger=None):
        super(ConcreteJob, self).__init__(options, queue, logger)

    def build_items(self):
        """
        main loop
        """

        # ping item
        self._ping()

        # detect libvirtd version
        self._get_version()

        # get information from libvirtd api
        self._get_vminfo()

    def _enqueue(self, key, value):

        item = LibVirtdItem(
            key=key,
            value=value,
            host=self.options['hostname']
        )
        self.queue.put(item, block=False)
        self.logger.debug(
            'Inserted to queue {key}:{value}'
            ''.format(key=key, value=value)
        )

    def _ping(self):
        """
        send ping item
        """

        self._enqueue('blackbird.libvirtd.ping', 1)
        self._enqueue('blackbird.libvirtd.version', __VERSION__)

    def _get_version(self):
        """
        detect libvirtd version

        $ libvirtd --version
        libvirtd (libvirt) N.N.N
        """

        version = 'Unknown'
        path = self.options['path']
        try:
            output = subprocess.Popen([path, '--version'],
                                      stdout=subprocess.PIPE).communicate()[0]
            ms = "{path} \(libvirt\) (\S+)".format(path=path)
            m = re.match(ms, output)
            if m:
                version = m.group(1)

        except OSError:
            self.logger.debug(
                'can not exec "{0} --version", failed to get libvirtd version'
                ''.format(path)
            )

        self._enqueue('libvirtd.version', version)

    def _get_vminfo(self):
        """
        Get instance information from libvirtd api
        """

        vm_sts = {
            0: 'nostate',
            1: 'running',
            2: 'blocked',
            3: 'paused',
            4: 'shutdown',
            5: 'shutoff',
            6: 'crashed',
            7: 'pmsuspended',
        }

        used_cpu = 0
        used_mem = 0
        vm_num = 0
        vm_status_num = {}

        try:
            conn = libvirt.openReadOnly(None)
        except Exception as e:
            self.logger.error(
                'Can not connect to libvirtd'
            )
            return

        # gather host capability
        _getinfo = conn.getInfo()
        self._enqueue('libvirtd.total.cpu', _getinfo[2])
        self._enqueue('libvirtd.total.memory', _getinfo[1])

        # gather vm information
        for vm_id in conn.listDomainsID():
            (_state, _max_mem, _mem, _num_cpu, _cpu_time) = \
                conn.lookupByID(vm_id).info()
            vm_num += 1
            used_cpu += _num_cpu
            used_mem += _mem

            _s = vm_sts[_state]
            if _s in vm_status_num:
                vm_status_num[_s] += 1
            else:
                vm_status_num[_s] = 1

        self._enqueue('libvirtd.used.cpu', used_cpu)
        self._enqueue('libvirtd.used.memory', used_mem)
        self._enqueue('libvirtd.vm.number.total', vm_num)

        for s in vm_sts.values():
            key = 'libvirtd.vm.%s.number' % (s)
            num = vm_sts[s] if s in vm_sts else 0
            self._enqueue(key, num)


class LibVirtdItem(base.ItemBase):
    """
    Enqued item.
    """

    def __init__(self, key, value, host):
        super(LibVirtdItem, self).__init__(key, value, host)

        self._data = {}
        self._generate()

    @property
    def data(self):
        return self._data

    def _generate(self):
        self._data['key'] = self.key
        self._data['value'] = self.value
        self._data['host'] = self.host
        self._data['clock'] = self.clock


class Validator(base.ValidatorBase):
    """
    Validate configuration.
    """

    def __init__(self):
        self.__spec = None

    @property
    def spec(self):
        self.__spec = (
            "[{0}]".format(__name__),
            "path=string(default='/usr/sbin/libvirtd')",
            "hostname=string(default={0})".format(self.detect_hostname()),
        )
        return self.__spec
