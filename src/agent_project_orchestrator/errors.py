class APOError(RuntimeError):
    pass

class ValidationError(APOError):
    pass

class TransitionError(APOError):
    pass

class GitStateError(APOError):
    pass
