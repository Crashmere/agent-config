#!/bin/sh
set -eu

# Apply the supported firmware controls on the G733 host.
printf '80\n' > /sys/class/power_supply/BAT0/charge_control_end_threshold
printf 'balanced\n' > /sys/firmware/acpi/platform_profile
for preference in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/energy_performance_preference; do
    printf 'balance_power\n' > "$preference"
done
printf '0\n' > /sys/devices/system/cpu/cpufreq/boost
# Match processor.max_cstate=1 immediately on an already running acpi_idle host.
for state in /sys/devices/system/cpu/cpu[0-9]*/cpuidle/state[2-9]/disable; do
    [ -e "$state" ] || continue
    printf '1\n' > "$state"
done
printf '0\n' > /sys/class/leds/asus::kbd_backlight/brightness
