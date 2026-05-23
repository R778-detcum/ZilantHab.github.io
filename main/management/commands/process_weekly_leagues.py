from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from main.models import UserLeagueMembership, League, LeagueInstance, Profile
from collections import defaultdict

class Command(BaseCommand):
    help = 'Еженедельное перераспределение пользователей по лигам'

    def handle(self, *args, **options):
        today = timezone.now().date()
        last_week_start = today - timedelta(days=today.weekday() + 7)
        memberships = UserLeagueMembership.objects.filter(week_start=last_week_start).select_related('user', 'league_instance')
        groups = defaultdict(list)
        for m in memberships:
            groups[m.league_instance].append(m)

        for league_instance, members in groups.items():
            members.sort(key=lambda x: x.weekly_xp, reverse=True)
            total = len(members)
            promote_count = min(10, total // 3)
            demote_count = min(10, total // 3)

            # Повышение: первые promote_count
            for i in range(promote_count):
                user = members[i].user
                new_league = League.objects.filter(rank_order=league_instance.league.rank_order + 1).first()
                if new_league:
                    new_instance, _ = LeagueInstance.objects.get_or_create(league=new_league, instance_number=league_instance.instance_number)
                    UserLeagueMembership.objects.create(
                        user=user,
                        league_instance=new_instance,
                        week_start=today,
                        weekly_xp=0
                    )
                else:
                    # остаются в той же
                    UserLeagueMembership.objects.create(
                        user=user,
                        league_instance=league_instance,
                        week_start=today,
                        weekly_xp=0
                    )

            # Понижение: последние demote_count
            for i in range(demote_count):
                user = members[total - 1 - i].user
                new_league = League.objects.filter(rank_order=league_instance.league.rank_order - 1).first()
                if new_league:
                    new_instance, _ = LeagueInstance.objects.get_or_create(league=new_league, instance_number=league_instance.instance_number)
                    UserLeagueMembership.objects.create(
                        user=user,
                        league_instance=new_instance,
                        week_start=today,
                        weekly_xp=0
                    )
                else:
                    UserLeagueMembership.objects.create(
                        user=user,
                        league_instance=league_instance,
                        week_start=today,
                        weekly_xp=0
                    )

            # Остальные остаются в своей лиге
            for i in range(promote_count, total - demote_count):
                user = members[i].user
                UserLeagueMembership.objects.create(
                    user=user,
                    league_instance=league_instance,
                    week_start=today,
                    weekly_xp=0
                )

        self.stdout.write(self.style.SUCCESS('Лиги обновлены'))