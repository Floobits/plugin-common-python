import os
import sys
import webbrowser

try:
    from . import base
    from .. import api, shared as G, utils
    from ... import editor
    from ..protocols import no_reconnect
    assert api and G and utils
except (ImportError, ValueError):
    import base
    from floo import editor
    from floo.common.protocols import no_reconnect
    from .. import api, shared as G, utils

WELCOME_MSG = """Welcome %s!\n\nYou are all set to collaborate.

You may want to check out our docs at https://%s/help/plugins/sublime#usage"""


class RequestCredentialsHandler(base.BaseHandler):
    PROTOCOL = no_reconnect.NoReconnectProto

    def __init__(self, token):
        super(RequestCredentialsHandler, self).__init__()
        self.token = token

    def build_protocol(self, *args):
        proto = super(RequestCredentialsHandler, self).build_protocol(*args)

        def on_stop():
            self.emit('end', False)
            self.stop()

        proto.once('stop', on_stop)
        return proto

    def is_ready(self):
        return False

    def on_connect(self):
        webbrowser.open('https://%s/dash/link_editor/%s/%s' % (self.proto.host, self.codename, self.token))
        self.send({
            'name': 'request_credentials',
            'client': self.client,
            'platform': sys.platform,
            'token': self.token,
            'version': G.__VERSION__
        })

    def on_data(self, name, data):
        if name == 'credentials':
            s = utils.load_floorc_json()
            auth = s.get('AUTH', {})
            auth[self.proto.host] = data['credentials']
            s['AUTH'] = auth
            utils.save_floorc_json(s)
            utils.reload_settings()
            success = utils.can_auth(self.proto.host)
            if not success:
                editor.error_message('Something went wrong. See https://%s/help/floorc to complete the installation.' % self.proto.host)
                api.send_error('No username or secret')
            else:
                p = os.path.join(G.BASE_DIR, 'welcome.md')
                with open(p, 'w') as fd:
                    text = WELCOME_MSG % (G.AUTH.get(self.proto.host, {}).get('username'), self.proto.host)
                    fd.write(text)
                editor.open_file(p)
            self.emit('end', success)
            self.stop()
