# -*- coding: utf-8 -*-


def boot(ini, stage):
    if ini:
        try:
            import newrelic.agent
            newrelic.agent.initialize(ini, stage)
        except Exception as e:
            raise Exception('Failed to init new relic agent %s' % e)
