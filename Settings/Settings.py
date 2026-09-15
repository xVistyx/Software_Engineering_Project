from interfaces import ISettings

class Settings(ISettings):
    DEFAULTS = {'defaultMinutes': 45, 'breakReminders': True, 'sounds': False, 'strictMode': False}

    def handle(self, action, content, data):
        if action == 'update_settings':
            for key, value in content.items():
                if key not in self.DEFAULTS:
                    raise ValueError('Unknown setting')
                if key == 'defaultMinutes':
                    if type(value) is not int or not 1 <= value <= 480:
                        raise ValueError('Invalid default duration')
                elif type(value) is not bool:
                    raise ValueError('Settings switches require a boolean')
            data['settings'].update(content)
        if action == 'update_blocklist':
            sites = content.get('sites')
            if not isinstance(sites, list) or len(sites) > 500 or any(not isinstance(s, str) or not s or len(s) > 253 for s in sites):
                raise ValueError('Invalid blocklist')
            data['blocklist'] = list(dict.fromkeys(sites))
        return {'sites': data['blocklist']} if action.endswith('blocklist') else data['settings']

    def __init__(self):
        pass
    def view_settings(self):
        pass
