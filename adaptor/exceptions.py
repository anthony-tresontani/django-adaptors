class AdaptorError(Exception):
    pass


class FieldError(AdaptorError, ValueError):
    pass


class ForeignKeyFieldError(FieldError):
    def __init__(self, msg, model, value):
        self.model = model
        self.value = value
        self.msg = msg
        super(ForeignKeyFieldError, self).__init__(self.msg)


class FieldValueMissing(FieldError):
    def __init__(self, field_name):
        super(FieldValueMissing, self).__init__("No value found for field %s" % field_name)


class ChoiceError(AdaptorError, ValueError):
    pass


