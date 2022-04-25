#!/usr/bin/env python3

import json
import logging
import socket

from ops.framework import (
    StoredState,
    EventBase,
    ObjectEvents,
    EventSource,
    Object)


class ReadyRunnerEvent(EventBase):
    pass

class ZosciConfigRunnerEvents(ObjectEvents):
    ready_runner = EventSource(ReadyRunnerEvent)


class ZosciConfigRunners(Object):

    on = ZosciConfigRunnerEvents()
    _stored = StoredState()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        self.this_unit = self.framework.model.unit
        self.framework.observe(
            charm.on[relation_name].relation_changed,
            self.on_changed)

    def on_changed(self, event):
        logging.info("ZosciConfigRunners on_changed")
        self.on.ready_runner.emit()

    def set_conn_data(self, pub_key):
        logging.info("Setting pub key")
        if self.runner_relation:
            self.runner_relation.data[self.this_unit]["ssh-pub-key"] = pub_key

    def get_runner_info(self):
        runners = {}
        if self.runner_relation:
            for u in self.runner_relation.units:
                if self.runner_relation.data[u].get("ssh-pub-key"):
                    runners[u.name] = {
                        'pub_key': self.runner_relation.data[u]["ssh-pub-key"],
                        'ip': self.runner_relation.data[u]['ingress-address']}
        return runners

    @property
    def runner_relation(self):
        return self.framework.model.get_relation(self.relation_name)
