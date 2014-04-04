import gettext
import __builtin__

__builtin__._ = gettext.gettext

from shadowcraft.calcs import DamageCalculator
from shadowcraft.core import exceptions

class RogueDamageCalculator(DamageCalculator):
    # Functions of general use to rogue damage calculation go here. If a
    # calculation will reasonably used for multiple classes, it should go in
    # calcs.DamageCalculator instead. If its a specific intermediate
    # value useful to only your calculations, when you extend this you should
    # put the calculations in your object. But there are things - like
    # backstab damage as a function of AP - that (almost) any rogue damage
    # calculator will need to know, so things like that go here.
    
    normalize_ep_stat = 'agi' #use 'dps' to prevent normalization
    # removed default_ep_stats: 'str', 'spell_hit', 'spell_exp'
    default_ep_stats = ['agi', 'haste', 'crit', 'mastery', 'ap', 'multistrike', 'readiness']
    melee_attacks = ['mh_autoattack_hits', 'oh_autoattack_hits', 'mh_shadow_blade', 'oh_shadow_blade', 'autoattack', 'shadow_blades',
                     'eviscerate', 'envenom', 'ambush', 'garrote',
                     'sinister_strike', 'revealing_strike', 'main_gauche', 'mh_killing_spree', 'oh_killing_spree',
                     'backstab', 'hemorrhage', 
                     'mutilate', 'mh_mutilate', 'oh_mutilate', 'dispatch']
    other_attacks = ['deadly_instant_poison']
    aoe_attacks = ['fan_of_knives', 'crimson_tempest']
    dot_ticks = ['rupture_ticks', 'garrote_ticks', 'deadly_poison', 'hemorrhage_dot']
    ranged_attacks = ['shuriken_toss', 'throw']
    non_dot_attacks = melee_attacks + ranged_attacks + aoe_attacks
    all_attacks = melee_attacks + ranged_attacks + dot_ticks + aoe_attacks + other_attacks
    
    assassination_mastery_conversion = .035
    combat_mastery_conversion = .02
    subtlety_mastery_conversion = .03
    assassination_readiness_conversion = 1.0
    combat_readiness_conversion = 1.0
    subtlety_readiness_conversion = 1.0
    
    passive_assassasins_resolve = 1.20
    passive_sanguinary_veins = 1.35
    passive_vitality_ap = 1.40
    passive_vitality_energy = 1.2
        
    ability_info = {
            'ambush':              (60, 'strike'),
            'backstab':            (35, 'strike'),
            'dispatch':            (30, 'strike'),
            'envenom':             (35, 'strike'),
            'eviscerate':          (35, 'strike'),
            'garrote':             (45, 'strike'),
            'hemorrhage':          (30, 'strike'),
            'mutilate':            (55, 'strike'),
            'recuperate':          (30, 'buff'),
            'revealing_strike':    (40, 'strike'),
            'rupture':             (25, 'strike'),
            'sinister_strike':     (50, 'strike'),
            'slice_and_dice':      (25, 'buff'),
            'tricks_of_the_trade': (15, 'buff'),
            'shuriken_toss':       (40, 'strike'),
            'shiv':                (20, 'strike'),
            'feint':               (20, 'buff'),
    }
    ability_cds = {
            'tricks_of_the_trade': 30,
            'blind':               90,
            'kick':                15,
            'kidney_shot':         20,
            'shiv':                8,
            'vanish':              120,
            'shadow_blades':       180,
            'vendetta':            120,
            'adrenaline_rush':     180,
            'killing_spree':       120,
            'shadow_dance':        60,
            'shadowmeld':          120,
            'marked_for_death':    60,
            'preparation':         300,
        }
    
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == 'level':
            self._set_constants_for_level()

    def _set_constants_for_level(self):
        super(RogueDamageCalculator, self)._set_constants_for_level()
        self.normalize_ep_stat = self.get_adv_param('norm_ep_stat', self.settings.default_ep_stat, ignore_bounds=True)
        # We only check race here (instead of calcs) because we can assume it's an agi food buff and it applies to every possible rogue calc
        # Otherwise we would be obligated to have a series of conditions to check for classes
        if self.race.epicurean:
            self.stats.agi += self.buffs.buff_agi(just_food=True)
        if self.settings.is_pvp:
            self.default_ep_stats.append('pvp_power')
        for proc in self.stats.procs.get_all_procs_for_stat():
            if proc == 'synapse_springs':
                self.stats.procs.synapse_springs['value'] = {'agi': self.tradeskill_bonus('synapse_springs')}
            if proc == 'lifeblood':
                self.stats.procs.lifeblood['value'] = {'haste': self.tradeskill_bonus('master_of_anatomy')}


        # These factors are taken from sc_spell_data.inc in SimulationCraft.
        # At some point we should automate the process to fetch them. Numbers
        # in comments show the id for the spell effect, not the spell itself,
        # unless otherwise stated.
        # 1246.298583984375000
        self.spell_scaling_for_level = self.tools.get_spell_scaling('rogue', self.level)
        self.vw_percentage_dmg = .160 # spellID 79136
        self.dp_percentage_dmg = .213 # spellID 2818
        self.wp_percentage_dmg = .120 # spellID 8680
        self.ip_percentage_dmg = .109 # spellID 113780
    
    def tradeskill_bonus(self, tradeskill='base'):
        # Hardcoded to use maxed tradeskills for the character level.
        tradeskills = ('skill', 'base', 'master_of_anatomy', 'lifeblood', 'synapse_springs')
        if self.level == 100:
            return (600, 320, 480, 2880, 1920)[tradeskills.index(tradeskill)]
        tradeskill_base_bonus = {
            (01, 60): (0, None, None, None, 0),
            (60, 70): (300, 9,   9,   70,   0),
            (70, 80): (375, 12,  12,  120,  0),
            (80, 85): (450, 20,  20,  240,  480),
            (85, 90): (525, 80,  80,  480,  480),
            (90, 95): (600, 320, 480, 2880, 2940)
        }

        for i, j in tradeskill_base_bonus.keys():
            if self.level in range(i, j):
                return tradeskill_base_bonus[(i, j)][tradeskills.index(tradeskill)]
            
    def setup_unique_procs_for_class(self):
        if getattr(self.stats.procs, 'legendary_capacitive_meta'):
            #1.789 mut, 1.136 com, 1.114 sub
            if self.settings.is_assassination_rogue():
                getattr(self.stats.procs, 'legendary_capacitive_meta').proc_rate_modifier = 1.789
            elif self.settings.is_combat_rogue():
                getattr(self.stats.procs, 'legendary_capacitive_meta').proc_rate_modifier = 1.136
            elif self.settings.is_subtlety_rogue():
                getattr(self.stats.procs, 'legendary_capacitive_meta').proc_rate_modifier = 1.114

        if getattr(self.stats.procs, 'fury_of_xuen'):
            #1.55 mut, 1.15 com, 1.0 sub
            if self.settings.is_assassination_rogue():
                getattr(self.stats.procs, 'fury_of_xuen').proc_rate_modifier = 1.55
            elif self.settings.is_combat_rogue():
                getattr(self.stats.procs, 'fury_of_xuen').proc_rate_modifier = 1.15
            elif self.settings.is_subtlety_rogue():
                getattr(self.stats.procs, 'fury_of_xuen').proc_rate_modifier = 1.0

    def get_factor(self, avg, delta=0):
        avg_for_level = avg * self.spell_scaling_for_level
        if delta == 0:
            return round(avg_for_level)
        else:
            min = round(avg_for_level * (1 - delta / 2))
            max = round(avg_for_level * (1 + delta / 2))
            return (min + max) / 2 # Not rounded: this is the average for us.

    def get_weapon_damage_bonus(self):
        # Override this in your modeler to implement weapon damage boosts
        # such as Unheeded Warning.
        return 0

    def get_weapon_damage(self, hand, ap, is_normalized=True):
        weapon = getattr(self.stats, hand)
        if is_normalized:
            damage = weapon.normalized_damage(ap) + self.get_weapon_damage_bonus()
        else:
            damage = weapon.damage(ap) + self.get_weapon_damage_bonus()
        return damage

    def oh_penalty(self):
        if self.settings.is_combat_rogue():
            return .875
        else:
            return .5

    def get_modifiers(self, *args, **kwargs):
        # A note on stacking: both executioner and potent poisons are expected
        # to stack additively as per my notes on issue #12. In mists they don't
        # have anything to stack additively with.
        base_modifier = 1
        kwargs.setdefault('mastery', None)
        if 'executioner' in args and self.settings.is_subtlety_rogue():
            base_modifier += self.subtlety_mastery_conversion * self.stats.get_mastery_from_rating(kwargs['mastery'])
        if 'potent_poisons' in args and self.settings.is_assassination_rogue():
            base_modifier += self.assassination_mastery_conversion * self.stats.get_mastery_from_rating(kwargs['mastery'])
        # Assassasins's Resolve
        if self.settings.is_assassination_rogue():
            base_modifier *= self.passive_assassasins_resolve
        # Sanguinary Vein
        kwargs.setdefault('is_bleeding', True)
        if kwargs['is_bleeding'] and self.settings.is_subtlety_rogue():
            base_modifier *= self.passive_sanguinary_veins
        # Raid modifiers
        kwargs.setdefault('armor', None)
        ability_type_check = 0
        for i in ['physical', 'bleed', 'spell']:
            if i in args:
                ability_type_check += 1
                base_modifier *= self.raid_settings_modifiers(i, kwargs['armor'])
        assert ability_type_check == 1

        crit_modifier = self.crit_damage_modifiers()

        return base_modifier, crit_modifier

    def mh_damage(self, ap, armor=None, is_bleeding=True):
        weapon_damage = self.get_weapon_damage('mh', ap, is_normalized=False)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)

        damage = weapon_damage * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def oh_damage(self, ap, armor=None, is_bleeding=True):
        weapon_damage = self.get_weapon_damage('oh', ap, is_normalized=False)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)

        damage = self.oh_penalty() * weapon_damage * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage
    
    def mh_shuriken(self, ap, armor=None, is_bleeding=True):
        return .75 * mh_damage(ap, armor=armor, is_bleeding=is_bleeding)
    
    def oh_shuriken(self, ap, armor=None, is_bleeding=True):
        return .75 * oh_damage(ap, armor=armor, is_bleeding=is_bleeding)

    def backstab_damage(self, ap, armor=None, is_bleeding=True):
        weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)

        damage = 3.80 * (weapon_damage) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def dispatch_damage(self, ap, armor=None):
        weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        damage = [3.31, 4.80][self.stats.mh.type == 'dagger'] * (weapon_damage) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def mh_mutilate_damage(self, ap, armor=None):
        mh_weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        mh_damage = [1.37, 2.0][self.stats.mh.type == 'dagger'] * (mh_weapon_damage) * mult
        crit_mh_damage = mh_damage * crit_mult

        return mh_damage, crit_mh_damage

    def oh_mutilate_damage(self, ap, armor=None):
        oh_weapon_damage = self.get_weapon_damage('oh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        oh_damage = [1.37, 2.0][self.stats.mh.type == 'dagger'] * (self.oh_penalty() * oh_weapon_damage) * mult
        crit_oh_damage = oh_damage * crit_mult

        return oh_damage, crit_oh_damage

    def sinister_strike_damage(self, ap, armor=None, is_bleeding=True):
        weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)
        
        damage = [1.3, 1.88][self.stats.mh.type == 'dagger'] * (weapon_damage) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def hemorrhage_damage(self, ap, armor=None, is_bleeding=True):
        weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)

        percentage_damage_bonus = [1.6, 2.32][self.stats.mh.type == 'dagger']
        damage = percentage_damage_bonus * weapon_damage * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def hemorrhage_tick_damage(self, ap, from_crit_hemo=False, armor=None, is_bleeding=True):
        # Call this function twice to get all four crit/non-crit hemo values.
        hemo_damage = self.hemorrhage_damage(ap, armor=armor, is_bleeding=is_bleeding)[from_crit_hemo]
        mult, crit_mult = self.get_modifiers('bleed')

        tick_conversion_factor = .5 / 8
        tick_damage = hemo_damage * mult * tick_conversion_factor

        return tick_damage, tick_damage #can't crit in 5.0 anymore, the lazy solution

    def ambush_damage(self, ap, armor=None, is_bleeding=True):
        #TODO clean up
        weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)

        dagger_bonus = [1, 1.447][self.stats.mh.type == 'dagger']
        percentage_damage_bonus = 3.65 * dagger_bonus

        damage = percentage_damage_bonus * (weapon_damage) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def revealing_strike_damage(self, ap, armor=None):
        weapon_damage = self.get_weapon_damage('mh', ap, is_normalized=False)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        damage = 1.60 * weapon_damage * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def venomous_wounds_damage(self, ap, mastery=None):
        mult, crit_mult = self.get_modifiers('spell', 'potent_poisons', mastery=mastery)

        damage = (self.vw_percentage_dmg * ap) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def main_gauche_damage(self, ap, armor=None):
        weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        damage = 1.2 * weapon_damage * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def mh_killing_spree_damage(self, ap, armor=None):
        mh_weapon_damage = self.get_weapon_damage('mh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        mh_damage = mh_weapon_damage * mult
        crit_mh_damage = mh_damage * crit_mult

        return mh_damage, crit_mh_damage

    def oh_killing_spree_damage(self, ap, armor=None):
        oh_weapon_damage = self.get_weapon_damage('oh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        oh_damage = self.oh_penalty() * oh_weapon_damage * mult
        crit_oh_damage = oh_damage * crit_mult

        return oh_damage, crit_oh_damage
    
    def oh_killing_spree_damage_swap(self, ap, armor=None):
        #if not getattr(self.stats, 'oh2'):
        #    return self.oh_killing_spree_damage(ap, armor=armor)
        oh_weapon_damage = self.get_weapon_damage('eoh', ap)
        mult, crit_mult = self.get_modifiers('physical', armor=armor)

        oh_damage = self.oh_penalty() * oh_weapon_damage * mult
        crit_oh_damage = oh_damage * crit_mult

        return oh_damage, crit_oh_damage

    def mh_shadow_blades_damage(self, ap, is_bleeding=True):
        # TODO: normalized? percentage modifier? confirmed master poisoner stacks.
        mh_weapon_damage = self.get_weapon_damage('mh', ap, is_normalized=False)
        mult, crit_mult = self.get_modifiers('spell', is_bleeding=is_bleeding)

        mh_damage = mh_weapon_damage * mult
        crit_mh_damage = mh_damage * crit_mult

        return mh_damage, crit_mh_damage

    def oh_shadow_blades_damage(self, ap, is_bleeding=True):
        # TODO
        oh_weapon_damage = self.get_weapon_damage('oh', ap, is_normalized=False)
        mult, crit_mult = self.get_modifiers('spell', is_bleeding=is_bleeding)

        oh_damage = self.oh_penalty() * oh_weapon_damage * mult
        crit_oh_damage = oh_damage * crit_mult

        return oh_damage, crit_oh_damage

    def deadly_poison_tick_damage(self, ap, mastery=None, is_bleeding=True):
        mult, crit_mult = self.get_modifiers('spell', 'potent_poisons', mastery=mastery, is_bleeding=is_bleeding)

        tick_damage = (self.dp_percentage_dmg * ap) * mult
        crit_tick_damage = tick_damage * crit_mult

        return tick_damage, crit_tick_damage

    def deadly_instant_poison_damage(self, ap, mastery=None, is_bleeding=True):
        mult, crit_mult = self.get_modifiers('spell', 'potent_poisons', mastery=mastery, is_bleeding=is_bleeding)

        damage = (self.ip_percentage_dmg * ap) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def wound_poison_damage(self, ap, mastery=None, is_bleeding=True):
        mult, crit_mult = self.get_modifiers('spell', 'potent_poisons', mastery=mastery, is_bleeding=is_bleeding)

        damage = (self.wp_percentage_dmg * ap) * mult
        crit_damage = damage * crit_mult

        return damage, crit_damage

    def garrote_tick_damage(self, ap):
        mult, crit_mult = self.get_modifiers('bleed')

        tick_damage = (ap * 1 * 0.078) * mult
        crit_tick_damage = tick_damage * crit_mult

        return tick_damage, crit_tick_damage

    def rupture_tick_damage(self, ap, cp, mastery=None):
        #TODO: check the tick conversion logic
        mult, crit_mult = self.get_modifiers('bleed', 'executioner', mastery=mastery)

        ap_multiplier_tuple = (0, .025, .04, .05, .056, .062)
        tick_damage = (ap_multiplier_tuple[cp] * ap) * mult
        crit_tick_damage = tick_damage * crit_mult

        return tick_damage, crit_tick_damage

    def eviscerate_damage(self, ap, cp, armor=None, mastery=None, is_bleeding=True):
        mult, crit_mult = self.get_modifiers('physical', 'executioner', mastery=mastery, armor=armor, is_bleeding=is_bleeding)

        damage = (0.18 * cp * ap) * mult
        crit_damage = damage * crit_mult
        
        return damage, crit_damage

    def envenom_damage(self, ap, cp, mastery=None):
        mult, crit_mult = self.get_modifiers('spell', 'potent_poisons', mastery=mastery)

        damage = (0.134 * cp * ap) * mult
        crit_damage = damage * crit_mult
        
        return damage, crit_damage

    def fan_of_knives_damage(self, ap, armor=None, is_bleeding=True):
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)
        
        damage = (.175 * ap) * mult
        crit_damage = damage * crit_mult
        
        return damage, crit_damage

    def crimson_tempest_damage(self, ap, cp, armor=None, mastery=None):
        # TODO this doesn't look right
        mult, crit_mult = self.get_modifiers('physical', 'executioner', mastery=mastery, armor=armor)
        
        damage = (.0275 * cp * ap) * mult
        crit_damage = damage * crit_mult
        
        return damage, crit_damage

    def crimson_tempest_tick_damage(self, ap, cp, armor=None, mastery=None, from_crit_ct=False):
        ct_damage = self.crimson_tempest_damage(ap, cp, armor=armor, mastery=mastery)[from_crit_ct]
        mult, crit_mult = self.get_modifiers('bleed', is_bleeding=False)

        tick_conversion_factor = 2.4 / 6
        tick_damage = ct_damage * mult * tick_conversion_factor

        return tick_damage, tick_damage

    def shiv_damage(self, ap, armor=None, is_bleeding=True):
        # TODO this doesn't look right
        oh_weapon_damage = self.get_weapon_damage('oh', ap, is_normalized=False)
        mult, crit_mult = self.get_modifiers('physical', armor=armor, is_bleeding=is_bleeding)

        oh_damage = .25 * (self.oh_penalty() * oh_weapon_damage) * mult
        crit_oh_damage = oh_damage * crit_mult

        return oh_damage, crit_oh_damage

    def throw_damage(self, ap, is_bleeding=True):
        mult, crit_mult = self.get_modifiers('physical', is_bleeding=is_bleeding)
        
        damage = (.05 * ap) * mult
        crit_damage = damage * crit_mult
        
        return damage, crit_damage

    def shuriken_toss_damage(self, ap, is_bleeding=True):
        # TODO verify data
        mult, crit_mult = self.get_modifiers('physical', is_bleeding=is_bleeding)
        
        damage = (.6 * ap) * mult
        crit_damage = damage * crit_mult
        
        return damage, crit_damage
    
    def get_formula(self, name):
        formulas = {
            'backstab':              self.backstab_damage,
            'hemorrhage':            self.hemorrhage_damage,
            'sinister_strike':       self.sinister_strike_damage,
            'revealing_strike':      self.revealing_strike_damage,
            'main_gauche':           self.main_gauche_damage,
            'ambush':                self.ambush_damage,
            'eviscerate':            self.eviscerate_damage,
            'dispatch':              self.dispatch_damage,
            'mh_mutilate':           self.mh_mutilate_damage,
            'oh_mutilate':           self.oh_mutilate_damage,
            'mh_shadow_blade':       self.mh_shadow_blades_damage,
            'oh_shadow_blade':       self.oh_shadow_blades_damage,
            'venomous_wounds':       self.venomous_wounds_damage,
            'deadly_poison':         self.deadly_poison_tick_damage,
            'wound_poison':          self.wound_poison_damage,
            'deadly_instant_poison': self.deadly_instant_poison_damage,
            'shuriken_toss':         self.shuriken_toss_damage
        }
        return formulas[name]

    def get_spell_stats(self, ability, cost_mod=1.0):
        if ability == 'tricks_of_the_trade' and self.glyphs.tricks_of_the_trade:
            return (0, 'buff')
        
        cost = self.ability_info[ability][0] * cost_mod
        
        return (cost, self.ability_info[ability][1])
    
    def get_spell_cd(self, ability):
        cd_reduction_table = {'assassination': ['vanish', 'shadow_blades', 'vendetta'],
                              'combat': ['shadow_blades', 'adrenaline_rush', 'killing_spree'],
                              'subtlety': ['vanish', 'shadow_blades', 'shadow_dance']
                             }#Cloak, Evasion, Sprint affect all 3 specs, not needed in list
        
        #need to update list of affected abilities
        if ability in cd_reduction_table[self.settings.get_spec()]:
            return self.ability_cds[ability] * self.stats.get_readiness_multiplier_from_rating(readiness_conversion=self.readiness_spec_conversion)
        else:
            return self.ability_cds[ability]

    def melee_crit_rate(self, crit=None):
        # all rogues get 10% bonus crit, assumed to affect everything, .05 of base crit for everyone
        # should be coded better?
        base_crit = .05
        base_crit += self.stats.get_crit_from_rating(crit)
        base_crit += .1
        return base_crit + self.buffs.buff_all_crit() + self.race.get_racial_crit(is_day=self.settings.is_day) - self.melee_crit_reduction

    def spell_crit_rate(self, crit=None):
        # all rogues get 10% bonus crit, assumed to affect everything, .05 of base crit for everyone
        # should be coded better?
        base_crit = .05
        base_crit += self.stats.get_crit_from_rating(crit)
        base_crit += .1
        return base_crit + self.buffs.buff_all_crit() + self.race.get_racial_crit(is_day=self.settings.is_day) - self.spell_crit_reduction
