from src.models import ProgressStats


class ProgressTracker:
    def __init__(self, total: int):
        self.total = total
        self.success = 0
        self.errors = 0
        self.total_balance: float = 0.0
    
    @property
    def progress(self) -> int:
        return self.success + self.errors
    
    def increment_success(self):
        self.success += 1
    
    def increment_error(self):
        self.errors += 1
    
    def set_balance(self, balance: float):
        self.total_balance = balance
    
    def get_stats(self) -> ProgressStats:
        return ProgressStats(
            progress=self.progress,
            total=self.total,
            success=self.success,
            errors=self.errors,
            balance=self.total_balance,
        )
