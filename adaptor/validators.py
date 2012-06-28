import re

class GenericRegexValidator(object):
    def validate(self, value):
        return bool(re.match(self.regex, value))

def RegexValidator(name, regex):
    return type(name, (GenericRegexValidator,), {'regex':regex})
    
