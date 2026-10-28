#!/bin/sh
set -eu

# Read sysfs only: controller probes can wake a suspended GPU or SSD.
health=$(
    printf 'nas-health load="%s" ' "$(cat /proc/loadavg)"
    awk '/MemAvailable:/ {printf "mem_available_kib=%s ", $2}' /proc/meminfo
    for monitor in /sys/class/hwmon/hwmon*; do
        name=$(cat "$monitor/name")
        case "$name" in
            k10temp|nvme|asus|acpitz_0) ;;
            *) continue ;;
        esac
        for sensor in "$monitor"/temp*_input "$monitor"/fan*_input; do
            [ -r "$sensor" ] || continue
            printf '%s.%s.%s=%s ' "$name" "${monitor##*/}" "${sensor##*/}" "$(cat "$sensor")"
        done
    done
    for item in \
        /sys/firmware/acpi/platform_profile \
        /sys/devices/system/cpu/cpufreq/boost \
        /sys/bus/pci/devices/0000:01:00.0/power/runtime_status; do
        printf '%s=%s ' "${item##*/}" "$(cat "$item")"
    done
)
printf '%s\n' "$health"
