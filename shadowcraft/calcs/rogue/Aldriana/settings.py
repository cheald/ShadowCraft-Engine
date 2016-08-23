from shadowcraft.core import exceptions

class Settings(object):
    # Settings object for AldrianasRogueDamageCalculator.

    def __init__(self, cycle, response_time=.5, latency=.03, duration=300, adv_params=None,
                 merge_damage=True, num_boss_adds=0, feint_interval=0, default_ep_stat='ap', is_day=False, is_demon=False,
                 marked_for_death_resets=0, finisher_threshold=5):
        self.cycle = cycle
        self.response_time = response_time
        self.latency = latency
        self.duration = duration
        self.feint_interval = feint_interval
        self.is_day = is_day
        self.is_demon = is_demon
        self.num_boss_adds = max(num_boss_adds, 0)
        self.adv_params = self.interpret_adv_params(adv_params)
        self.default_ep_stat = default_ep_stat
        #per minute
        self.marked_for_death_resets=marked_for_death_resets

        #TODO: can be overridden by spec specific finisher thresholds
        self.finisher_threshold = finisher_threshold

    def interpret_adv_params(self, s=""):
        data = {}
        max_effects = 8
        current_effects = 0
        if s != "" and s:
            for e in s.split(';'):
                if e != "":
                    tmp = e.split(':')
                    try:
                        data[tmp[0].strip().lower()] = tmp[1].strip().lower() #strip() and lower() needed so that everyone is on the same page                        print data[tmp[0].strip().lower()] + ' : ' + tmp[0].strip().lower()
                        current_effects += 1
                        if current_effects == max_effects:
                            return data
                    except:
                        raise exceptions.InvalidInputException(_('Advanced Parameter ' + e + ' found corrupt. Properly structure params and try again.'))
        return data

    def is_assassination_rogue(self):
        return self.cycle._cycle_type == 'assassination'

    def is_combat_rogue(self):
        return self.cycle._cycle_type == 'combat'

    def is_subtlety_rogue(self):
        return self.cycle._cycle_type == 'subtlety'

class Cycle(object):
    # Base class for cycle objects.  Can't think of anything that particularly
    # needs to go here yet, but it seems worth keeping options open in that
    # respect.

    # When subclassing, define _cycle_type to be one of 'assassination',
    # 'combat', or 'subtlety' - this is how the damage calculator makes sure
    # you have an appropriate cycle object to go with your talent trees, etc.
    _cycle_type = ''


class AssassinationCycle(Cycle):
    _cycle_type = 'assassination'

    def __init__(self, kingsbane_with_vendetta ='just', exsang_with_vendetta='just', cp_builder='mutilate'):
        self.cp_builder = cp_builder #Allowed values: 'mutilate', 'fan_of_knives'
        #Cooldown scheduling and usage settings
        #Allowed values: 'just': Use cooldown if it aligns with vendetta but don't delay usages
        #                'only': Only use cooldown with vendetta
        self.kingsbane_with_vendetta = kingsbane_with_vendetta
        self.exsang_with_vendetta = exsang_with_vendetta

class OutlawCycle(Cycle):
    _cycle_type = 'outlaw'

    def __init__(self, blade_flurry=False, between_the_eyes_policy='shark',
                 jolly_roger_reroll=0, grand_melee_reroll=0, shark_reroll=0,
                 true_bearing_reroll=0, buried_treasure_reroll=0, broadsides_reroll=0):
        self.blade_flurry = bool(blade_flurry)
        self.between_the_eyes_policy = between_the_eyes_policy #Allowed values: 'shark', 'always', 'never'
        # RtB reroll thresholds, 0, 1, 2, 3
        # 0 means never reroll combos with this buff
        # 1 means reroll singles of buff
        # 2 means reroll doubles containing this buff
        # 3 means reroll triples containing this buff
        self.jolly_roger_reroll = jolly_roger_reroll
        self.grand_melee_reroll = grand_melee_reroll
        self.shark_reroll = shark_reroll
        self.true_bearing_reroll = true_bearing_reroll
        self.buried_treasure_reroll = buried_treasure_reroll
        self.broadsides_reroll = broadsides_reroll


class SubtletyCycle(Cycle):
    _cycle_type = 'subtlety'

    def __init__(self, cp_builder='backstab', positional_uptime=1.0, symbols_policy='just',
                 eviscerate_cps=5, finality_eviscerate_cps=5, nightblade_cps=5, finality_nightblade_cps=5, dfa_cps = 5,
                 dance_finishers_allowed=True):
        self.cp_builder = cp_builder #Allowed values: 'shuriken_storm', 'backstab' (implies gloomblade if selected and ssk during dance)
        self.positional_uptime = positional_uptime #Range 0.0 to 1.0, time behind target
        self.symbols_policy = symbols_policy #Allowed values:
                                             #'always' - use SoD every dance (macro)
                                             #'just'   - Only use SoD when needed to refresh
        #Allow finishers to be scheduled during dance
        self.dance_finishers_allowed= dance_finishers_allowed