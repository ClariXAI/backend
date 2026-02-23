from supabase import Client


class BaseRepository:
    def __init__(self, supabase: Client) -> None:
        self.supabase = supabase
