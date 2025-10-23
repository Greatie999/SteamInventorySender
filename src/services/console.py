import os

from src.models import ProgressStats


class ConsoleUI:
    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")
    
    @staticmethod
    def set_title(title: str):
        if os.name == "nt":
            os.system(f'title {title}')
    
    @staticmethod
    def update_title(stats: ProgressStats):
        title = (
            f"SteamInventorySender (${stats.balance:.2f}) | "
            f"{stats.progress}/{stats.total} | "
            f"Success: {stats.success} | "
            f"Errors: {stats.errors}"
        )
        ConsoleUI.set_title(title)
