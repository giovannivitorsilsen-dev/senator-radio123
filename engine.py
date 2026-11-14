"""Account-scoped scan and foreground batch execution."""
from dataclasses import dataclass


class StopRun(Exception):
    pass


@dataclass(frozen=True)
class Scan:
    owner: str
    targets: tuple


def scan(client, stopped=lambda: False):
    def checkpoint():
        if stopped():
            raise StopRun("Analisi interrotta.")
        if str(client.user_id) != owner:
            raise StopRun("Account cambiato. Ripeti l’analisi.")
    owner = str(client.user_id)
    if not client.user_id:
        raise StopRun("Accedi prima di analizzare.")
    checkpoint()
    before = client.user_info_v1(owner)
    checkpoint()
    followers = client.user_followers(owner, use_cache=False)
    checkpoint()
    following = client.user_following(owner, use_cache=False)
    checkpoint()
    after = client.user_info_v1(owner)
    checkpoint()
    sizes = len(followers), len(following)
    for profile in (before, after):
        if sizes != (profile.follower_count, profile.following_count):
            raise StopRun("Gli elenchi sono incompleti o sono cambiati. Ripeti l’analisi.")
    mutual_ids = {str(key) for key in followers}
    targets = tuple((str(key), value.username) for key, value in following.items()
                    if str(key) not in mutual_ids and str(key) != owner)
    return Scan(owner, targets)


def execute(client, snapshot, protected, stopped, report):
    for uid, name in snapshot.targets:
        if stopped():
            return
        if str(client.user_id) != snapshot.owner:
            raise StopRun("Account cambiato. Ripeti l’analisi.")
        if uid in protected:
            continue
        relation = client.user_friendship_v1(uid)
        if relation is None or str(relation.user_id) != uid:
            raise StopRun("Rapporto non verificabile. Operazione interrotta.")
        if relation.following is not True or relation.followed_by is not False:
            report(name, "saltato")
            continue
        if stopped():
            return
        if str(client.user_id) != snapshot.owner:
            raise StopRun("Account cambiato. Ripeti l’analisi.")
        try:
            confirmed = client.user_unfollow(uid)
        except Exception as err:
            raise StopRun(f"Esito sconosciuto per @{name}. Ripeti l’analisi.") from err
        if confirmed is not True:
            raise StopRun("Esito incerto. Ripeti l’analisi prima di proseguire.")
        report(name, "rimosso")
