import json
import math

RED = '\033[31m'
REDEND = '\033[0m'


def get_uld(elevation, flap, weight):
    """Gets the ULD by interpolating and using index locations from the QRH
    It grabs the weight one tonne up and below and the elevation INDEX position one up and below.
    It then interpolates using the percentage of the remaining index location."""
    weight_tonnes = weight / 1000
    print(weight_tonnes)
    flap = str(int(flap))
    wt_up = str(math.ceil(float(weight_tonnes)))
    wt_down = str(math.floor(float(weight_tonnes)))
    with open('ulds_q200.json') as ulds:
        uld_ = json.load(ulds)
    elevation_up = math.ceil(elevation)
    elevation_down = math.floor(elevation)
    # interpolating with the upper weight of the two elevation figures
    wt_up_up_data = uld_[flap][wt_up][elevation_up]
    wt_up_dwn_data = uld_[flap][wt_up][elevation_down]
    uld_up_wt = round(wt_up_dwn_data + ((wt_up_up_data - wt_up_dwn_data) * (elevation - elevation_down)))
    # interpolating with the lower weight of the two elevation figures
    wt_dwn_up_data = uld_[flap][wt_down][elevation_up]
    wt_dwn_dwn_data = uld_[flap][wt_down][elevation_down]
    uld_dwn_wt = round(wt_dwn_dwn_data + ((wt_dwn_up_data - wt_dwn_dwn_data) * (elevation - elevation_down)))
    # interpolating for weight between the two elevation interpolated figures
    final_uld = round(uld_dwn_wt + (uld_up_wt - uld_dwn_wt) * (float(weight_tonnes) - int(wt_down)))

    return final_uld


def wind_correct_formulated(ULD, wind_comp, flap):
    """for every m above 450 ULD, take off 0.002m (0.3 change over 150) on top of the base 2.7 for every knot head
    for every m above 450 ULD, add 0.008m (1.2 change over 150) on top of the base 8.6 for every knot tail

    flap 35 (0.1 diff over 130) means take 0.00076923m on top of 2.7 base for every knot of head
    flap 35 (0.9 diff over 130) means add 0.00692308m on top base 8.8 for any over 420 for tail"""
    tail_more_than_10 = False
    flap = str(flap)
    if flap == "15":
        amount_above_base_ULD = ULD - 450
    else:
        amount_above_base_ULD = ULD - 420
    if wind_comp > 0:  # flap 15 headwind
        if flap == "15":
            factor_above_uld = amount_above_base_ULD * 0.002
            wind_corr_ULD = round(ULD - (wind_comp * (2.7 + factor_above_uld)))
        else:  # flap 35 headwind
            factor_above_uld = amount_above_base_ULD * 0.00076923
            wind_corr_ULD = round(ULD - (wind_comp * (2.7 + factor_above_uld)))

    else:  # tailwind (this differs between flap 15 and 35
        if flap == "15":
            factor_above_uld = amount_above_base_ULD * 0.008
            wind_corr_ULD = ULD - round((wind_comp * (8.6 + factor_above_uld)))
        else:  # flap 35 tailwind
            factor_above_uld = amount_above_base_ULD * 0.00692308
            wind_corr_ULD = ULD - round((wind_comp * (8.8 + factor_above_uld)))
    """I dont know what the addit for tailwind over 10 is. I wasn't given an AOM which has the chart"""
    if wind_comp < -10:  # if the wind is more than 10 knot tail, add 1.6% for every knot over 10t
        tail_more_than_10 = True
        if flap == "15":
            factor_above_uld = (amount_above_base_ULD / 100)
            ten_tail_ULD = ULD - round((-10 * (8.6 + factor_above_uld)))
            wind_corr_ULD = int(ten_tail_ULD * (1 + ((abs(wind_comp) - 10) * 1.6) / 100))
        else:
            factor_above_uld = (amount_above_base_ULD / 100)
            ten_tail_ULD = ULD - round((-10 * (8.8 + factor_above_uld)))
            wind_corr_ULD = int(ten_tail_ULD * (1 + ((abs(wind_comp) - 10) * 1.6) / 100))
    return int(wind_corr_ULD), tail_more_than_10


def slope_corrected(slope, wind_corrected_ld, flap):
    """If the slope is greater than 0, the slope is going uphill so the distance will be shorter
    IF the slope is less than 0 however, the slope is downhill and the distance increases."""
    flap = str(flap)
    if flap == "15":
        if slope < 0:  # if the slope is downhill
            slope_correct = wind_corrected_ld + (wind_corrected_ld * (abs(slope) * 0.1))
        else:  # if the slope is uphill
            slope_correct = wind_corrected_ld - (wind_corrected_ld * (abs(slope) * 0.067))

    else:  # flap 35
        if slope < 0:  # if the slope is downhill
            slope_correct = wind_corrected_ld + (wind_corrected_ld * (abs(slope) * 0.095))
        else:  # if the slope is uphill
            slope_correct = wind_corrected_ld - (wind_corrected_ld * (abs(slope) * 0.071))
    return int(slope_correct)


def get_v_speeds(weight, flap, vapp_addit, ice):
    flap = str(flap)
    weight = str((math.ceil(weight / 500) * 500) / 1000)
    print(weight)
    with open('ref_speeds.json') as file:
        f = json.load(file)
    vref = f[flap][weight]
    vapp = int(vref) + vapp_addit
    if flap == "15":
        vref_ice = vref + 10
    else:
        vref_ice = vref + 5
    if ice == "On":
        vapp = vref_ice

    return vapp, vref, vref_ice


def vapp_corrections(wind_slope_ld, vref, vref_addit):
    """Take the wind and slope corrected landing distance and apply increase in distance by using formula
    vpp^2 / vref^2 which gives the multiplier to the LD"""

    percent_increase = (vref + vref_addit) ** 2 / vref ** 2

    vapp_adjusted_ld = wind_slope_ld * percent_increase
    print("Added", str(percent_increase)[2:4], "percent increase to landing distance which gives", vapp_adjusted_ld)

    return vapp_adjusted_ld, percent_increase


def ice_protect_addit(flap, prop_adjusted_ld):
    """If INCR REF switch on, add 16% for flap 15 and 10% for flap 35. """
    flap = str(int(flap))
    if flap == "15":
        ice_protect_adjusted_ld = prop_adjusted_ld * 1.16
    else:
        ice_protect_adjusted_ld = prop_adjusted_ld * 1.10

    return ice_protect_adjusted_ld


def abnormal_factor(ab_fctr, ICE_OFF_company_applied, ICE_ON_company_applied, bleeds, ice, tail_more_than_10, flap):
    """Take in the abnormal factor from the excel sheet and pull its factor from the Multipliers excel sheet
    Return the landing dis required after applying the factor to the distance with all factors applied
    except for company addit. Return BOTH the ice ON and OFF distances.
    Also bypass the EXTENDED DOOR OPEN and EXTENDED DOOR CLOSED factoring as it is a MLDW and WAT issue only"""
    print(ab_fctr, "Is the Abnormality")
    flap = str(flap)
    can_land_in_this_config = True
    if ab_fctr == "EXTENDED DOOR OPEN" or ab_fctr == "EXTENDED DOOR CLOSED":  # due to it being WAT and MLDW issue only
        multiplier = 1
        if bleeds == "On" or ice == "On":
            can_land_in_this_config = False
    elif ab_fctr == "INOP (A/S)":
        if flap == "15":
            multiplier = 1.45
        else:
            multiplier = 1.35
    else:  # if the MEL is the NWS
        multiplier = 1
    if tail_more_than_10:  # can't have tail more than 10kt per the supplement compatibility table for any of these MEL
        can_land_in_this_config = False
    distance = ICE_OFF_company_applied * multiplier
    ice_distance = ICE_ON_company_applied * multiplier

    print("Abnormal Multiplier is", multiplier, "which gives a distance of", distance, "ice OFF and", ice_distance,
          "with the ice ON")
    return int(distance), int(ice_distance), multiplier, can_land_in_this_config


def company_addit_dry_wet(wet_dry, ice_on_ld, ice_off_ld):
    """Adding 43% to the prop_adjusted_ld if dry and an additional 15% on top of that if wet 1222 = 1465"""
    if wet_dry == "Wet":
        ICE_ON_wet_dry_adjusted_ld = (ice_on_ld / 0.7) * 1.15
        ICE_OFF_wet_dry_adjusted_ld = (ice_off_ld / 0.7) * 1.15
    else:
        ICE_ON_wet_dry_adjusted_ld = ice_on_ld / 0.7
        ICE_OFF_wet_dry_adjusted_ld = ice_off_ld / 0.7

    return int(ICE_ON_wet_dry_adjusted_ld), int(ICE_OFF_wet_dry_adjusted_ld)


def get_torque_limits(temp, pressure_alt, vapp, bleeds):
    if bleeds == "On":
        temp = temp + 7
    if temp < 0:
        temp = 0
    if temp > 48:
        temp = 48
    if pressure_alt > 4000:
        pressure_alt = 4000
    if pressure_alt < 0:
        pressure_alt = 0
    temp = str(temp)
    pressure_alt = pressure_alt / 500
    with open('takeoff_torques.json') as file:
        torque = json.load(file)

    elev_up = math.ceil(pressure_alt)
    elev_down = math.floor(pressure_alt)
    temp_up = str(math.ceil(int(temp) / 2) * 2)
    temp_down = str(math.floor(int(temp) / 2) * 2)
    power = ["NTOP", "MTOP"]
    for lst in range(len(power)):
        # interpolating with the upper temp of the two elevation figures
        temp_up_up_data = torque[temp_up][elev_up][lst]
        temp_up_dwn_data = torque[temp_up][elev_down][lst]
        temp_up_wt = temp_up_dwn_data + ((temp_up_up_data - temp_up_dwn_data) * (pressure_alt - elev_down))
        # interpolating with the lower temp of the two elevation figures
        temp_dwn_up_data = torque[temp_down][elev_up][lst]
        temp_dwn_dwn_data = torque[temp_down][elev_down][lst]
        temp_dwn_wt = temp_dwn_dwn_data + ((temp_dwn_up_data - temp_dwn_dwn_data) * (pressure_alt - elev_down))

        torque_limit = (temp_up_wt + temp_dwn_wt) / 2

        power[lst] = torque_limit
    ntop = power[0]
    mtop = power[1]
    # if ntop > 97.5:
    #     ntop = 97.5
    # if mtop > 107.5:
    #     mtop = 107.5

    if vapp > 100:
        amount_over = vapp - 100
        for_every_two = amount_over / 2
        add_point_one = for_every_two * 0.1
        ntop = ntop + add_point_one
        mtop = mtop + add_point_one

    else:
        amount_under = 100 - vapp
        for_every_two = amount_under / 2
        subtract_point_one = for_every_two * 0.1
        ntop = ntop - subtract_point_one
        mtop = mtop - subtract_point_one

    if ntop > 97.5:
        ntop = 97.5
    if mtop > 107.5:
        mtop = 107.5

    return round(ntop, 2), round(mtop, 2)


def get_oei_climb(temp, elev, flap, weight):
    """scale is 0.002 units per dashed line
    Q200"""
    elev = elev * 500
    weight = weight / 1000
    elevation_envelope = -0.10
    if temp <= 28:
        temp_diff = 28 - temp
        elevation_envelope = temp_diff * 192
    if flap == "5":
        ref_weight = 12
        weight_change = 0.014
        if elev > elevation_envelope:
            print("Bottom scale")
            temp_change = 0.0018
            elev_change = 0.008
            base = 0.15

        else:
            print("Top scale")
            temp_change = 0.0003
            elev_change = 0.003
            base = 0.109
    else: # flap 15 missed
        ref_weight = 12
        weight_change = 0.013
        if elev > elevation_envelope:
            temp_change = 0.0018
            elev_change = 0.0075
            base = 0.138
        else:
            temp_change = 0.0003
            elev_change = 0.003
            base = 0.097

    temp_elev_units = base - (temp * temp_change) - ((elev / 1000) * elev_change)

    variance_from_12t = weight - ref_weight
    weight_units = variance_from_12t * weight_change
    initial_units = temp_elev_units - weight_units

    return round(initial_units * 100, 2)


def get_wat_limit(temp, flap, ice_protection, bleed, pressure_alt, test_case, ab_fctr):
    """Take in the temp, flap, bleed position and pressure altitude as parameters
    and return the max landing weight.
    Also trying to keep indexes in range as some temperatures and pressure altitudes are off charts.
    The minimum pressure alt for the chart is 0 and the max is 6000.
    The minimum temperature is 0 and the max is 48, even after the 11 degree addit"""
    off_chart_limits = False
    rpm = "MAX"
    flap = str(int(flap))
    MLDW = 15650

    if pressure_alt < 0:
        pressure_alt = 0
        off_chart_limits = True
    else:
        if pressure_alt > 6000:
            pressure_alt = 6000 / 500
            off_chart_limits = True
        else:
            pressure_alt = pressure_alt / 500
    if bleed == "On":
        temp = int(temp) + 7

    if temp > 48:
        temp = str(48)
        off_chart_limits = True
        if pressure_alt > 2:
            pressure_alt = 2
    else:
        if temp < 0:
            temp = str(0)
            off_chart_limits = True
        else:
            temp = str(temp)

    with open(f'wat_f15.json') as r:
        wat = json.load(r)
    elev_up = math.ceil(pressure_alt)
    elev_down = math.floor(pressure_alt)
    temp_up = str(math.ceil(int(temp) / 2) * 2)
    temp_down = str(math.floor(int(temp) / 2) * 2)

    # interpolating with the upper temp of the two elevation figures
    try:
        temp_up_up_data = wat[rpm][temp_up][elev_up]
    except Exception as err:
        print(RED + "ERROR" + REDEND, err, "TEST CASE", test_case)

    temp_up_dwn_data = wat[rpm][temp_up][elev_down]
    temp_up_wt = round(temp_up_dwn_data + ((temp_up_up_data - temp_up_dwn_data) * (pressure_alt - elev_down)))
    # interpolating with the lower temp of the two elevation figures
    temp_dwn_up_data = wat[rpm][temp_down][elev_up]
    temp_dwn_dwn_data = wat[rpm][temp_down][elev_down]
    temp_dwn_wt = round(temp_dwn_dwn_data + ((temp_dwn_up_data - temp_dwn_dwn_data) * (pressure_alt - elev_down)))

    wat_limit = int((temp_up_wt + temp_dwn_wt) / 2)
    # No change to WAT limit when ice protection is on

    print("WAT limit BEFORE abnormal restriction applied", wat_limit)
    if ab_fctr == "EXTENDED DOOR CLOSED":
        # this is in reference to AFM supplement 7 (Reduction in WAT weight) and
        # Bombardier Service Letter DH8-400-SL-32-001B (Ferry with Gear Doors Open) or the form on comply (MLW)

        if flap == "15":
            wat_limit = wat_limit - 1200
        else:
            wat_limit = wat_limit - 1200
        print("WAT limit after abnormal restriction applied", wat_limit)
    if ab_fctr == "EXTENDED DOOR OPEN":
        if flap == "15":
            wat_limit = wat_limit - 2100
        else:
            wat_limit = wat_limit - 2100
        print("WAT limit after abnormal restriction applied", wat_limit)

    if flap == "35":  # Assumption is that aircraft will continue to land at flap 35
        return 15650, MLDW, off_chart_limits
    if flap == "10" or flap == "5" or flap == "0":  # Should be able to climb with no WAT limit at these flap settings
        return 15650, MLDW, off_chart_limits

    return wat_limit, MLDW, off_chart_limits


def max_landing_wt_lda(lda, ice, ICE_ON_dry_wet, ICE_OFF_dry_wet, flap, weight, unfact_uld):
    """Find the ratio between the landing distance required and the unfactored ULD which returns a multiplier ratio
    Divide the landing distance available by the ratio to find the relative unfactored ULD
    Get the difference between the maximum (LDA based) ULD and the current ULD and divide by 22.5 for flap 15 or
    16 for flap 35 and multiply by 1000 (This is ULD difference for every tonne) this will give the weight to
    add onto the current landing weight which will give the max field landing weight.
    This is correct for the Q200"""
    flap = str(flap)
    if ice == "On":
        ld_required = ICE_ON_dry_wet
    else:
        ld_required = ICE_OFF_dry_wet

    if flap == "15":
        ratio = ld_required / unfact_uld
        max_unfact_uld = lda / ratio
        diff_between_ulds = max_unfact_uld - unfact_uld
        final = ((diff_between_ulds / 22.5) * 1000) + weight
    else:
        ratio = ld_required / unfact_uld
        max_unfact_uld = lda / ratio
        diff_between_ulds = max_unfact_uld - unfact_uld
        final = ((diff_between_ulds / 16) * 1000) + weight
    return int(final)


def max_brake_energy_wt(flap, temp, elev, weight, head_tail):
    """ example using flap 15...
    for every X degrees C, increase by Y units (0.021 per degree). starting at 0 degrees base of 5.65 at sea
    level.
    add 0.25 for every 1000' elevation.
    starting from 12t. every 1t = 1.36 units
    + 2.6 for every 10kt tail
    - 0.8 for every 10 kt tail """
    weight = int(weight) / 1000
    flap = str(flap)
    temp = int(temp)
    elev = int(elev * 500)
    head_tail = int(head_tail)
    max_brake_limit = 22.54
    if flap == "15":
        temp_change = 0.021
        base = 5.65
        elev_change = 0.25
        ref_weight = 12
        weight_change = 1.36
        tail_change = 0.26
        head_change = 0.08
    else:
        temp_change = 0.018
        base = 4.6
        elev_change = 0.2
        ref_weight = 12
        weight_change = 0.9
        tail_change = 0.26
        head_change = 0.08

    temp_elev_units = base + (temp * temp_change) + ((elev / 1000) * elev_change)
    variance_from_14t = weight - ref_weight
    weight_units = variance_from_14t * weight_change
    initial_units = temp_elev_units + weight_units
    print(initial_units)
    if head_tail < 0:
        final_brake_energy = initial_units + (abs(head_tail) * tail_change)
    else:
        final_brake_energy = initial_units - (abs(head_tail) * head_change)
    print(final_brake_energy, "is the brake energy")
    difference_between_current_and_max = max_brake_limit - final_brake_energy
    max_weight = ref_weight + ((weight_units + difference_between_current_and_max) / weight_change)
    print(int(max_weight * 1000), "Is the max brake energy weight for given conditions")
    return int(max_weight * 1000)


def final_max_weight(max_wat, max_field, max_brake_nrg_weight, MLDW, off_chart):
    """Find and return the lowest weight out of all provided. Also add * to any code where the wat weight
    used a parameter that was off chart."""
    weights = [max_wat, max_field, max_brake_nrg_weight, MLDW]
    # Find the minimum weight
    min_weight = min(weights)

    # Assign the corresponding code
    if min_weight == max_wat:
        code_max = "(c)"
    elif min_weight == max_field:
        code_max = "(f)"
    elif min_weight == max_brake_nrg_weight:
        code_max = "(b)"
    else:
        code_max = "(s)"

    # Add * if off_chart is True
    if off_chart:
        code_max += "*"

    if off_chart:
        max_weight = str(min_weight) + code_max + "^"
    else:
        max_weight = str(min_weight) + code_max
    return max_weight
