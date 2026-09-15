#!/usr/bin/env bash
# hyprfetch 2.0 — live system monitor, GUI cyberdeck, and terminal dashboard
# Supports:
#   ./hyprfetch.sh          (Launches Cyberdeck GUI if desktop active, else TUI)
#   ./hyprfetch.sh --gui    (Launches PyQt6/PySide6 Cyberdeck GUI)
#   ./hyprfetch.sh --tui    (Launches Python-powered TUI companion with sparklines)
#   ./hyprfetch.sh --json   (Outputs machine telemetry JSON)
#   ./hyprfetch.sh --bench      (Runs CPU/GPU/RAM/Disk benchmark suite)
#   ./hyprfetch.sh --gpu-info   (Shows detailed GPU information)
#   ./hyprfetch.sh --self-test  (Checks HyprFetch's own dependencies/subsystems)
#   ./hyprfetch.sh --diag       (Runs automatic anomaly diagnosis)
#   ./hyprfetch.sh --bash       (Runs standalone pure-bash animated neofetch monitor)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ENTRY="${SCRIPT_DIR}/main.py"

# If Python entrypoint exists and not explicitly asking for pure bash:
if [ -f "$PYTHON_ENTRY" ] && command -v python3 >/dev/null 2>&1; then
    case "${1:-}" in
        --bash)
            shift
            # Fall through to pure bash implementation below
            ;;
        --gui)
            exec python3 "$PYTHON_ENTRY" --gui "$@"
            ;;
        --tui|--cli)
            exec python3 "$PYTHON_ENTRY" --tui "$@"
            ;;
        --json|--api)
            exec python3 "$PYTHON_ENTRY" --json "$@"
            ;;
        --bench)
            exec python3 "$PYTHON_ENTRY" --bench "$@"
            ;;
        --gpu-info)
            exec python3 "$PYTHON_ENTRY" --gpu-info "$@"
            ;;
        --self-test)
            exec python3 "$PYTHON_ENTRY" --self-test "$@"
            ;;
        --diag|--diagnose)
            exec python3 "$PYTHON_ENTRY" --diagnose "$@"
            ;;
        --help|-h)
            echo "HyprFetch 2.0 — Next-Generation Cyberpunk System Monitor"
            echo ""
            echo "Usage: ./hyprfetch.sh [OPTION]"
            echo ""
            echo "Options:"
            echo "  --gui         Launch PyQt6/PySide6 Cyberdeck GUI"
            echo "  --tui, --cli  Launch interactive terminal monitor with sparklines"
            echo "  --bash        Run pure lightweight Bash animated monitor"
            echo "  --json        Output raw system telemetry JSON"
            echo "  --bench       Run hardware performance benchmark suite"
            echo "  --gpu-info    Show detailed GPU information"
            echo "  --self-test   Check HyprFetch's own dependencies/subsystems"
            echo "  --diagnose, --diag  Run 'What the hell is happening?' diagnostic scan"
            echo "  --theme NAME  Set theme (nova, nebula, cyberpunk, matrix, arctic, amoled, minimal)"
            echo "  --help, -h    Display this help message"
            exit 0
            ;;
        *)
            # If no flag specified and GUI display exists, launch GUI; else launch TUI
            if [ -n "${WAYLAND_DISPLAY:-}" ] || [ -n "${DISPLAY:-}" ]; then
                exec python3 "$PYTHON_ENTRY" --gui "$@"
            else
                exec python3 "$PYTHON_ENTRY" --tui "$@"
            fi
            ;;
    esac
fi

# ==============================================================================
# PURE BASH IMPLEMENTATION (Fallback / Standalone Mode)
# ==============================================================================

ACCENT_CODE=${HYPRFETCH_ACCENT:-213}   # 256-color code, default magenta
ACCENT2_CODE=${HYPRFETCH_ACCENT2:-51}  # default cyan
STAT_REFRESH_SECS=1                    # how often stats are re-polled
ANIM_TICK_SECS=0.2                     # animation frame rate

ACCENT=$'\e['"38;5;${ACCENT_CODE}"'m'
ACCENT2=$'\e['"38;5;${ACCENT2_CODE}"'m'
DIM=$'\e[38;5;240m'
RESET=$'\e[0m'
BOLD=$'\e[1m'

TICKS_PER_REFRESH=$(awk -v a="$STAT_REFRESH_SECS" -v b="$ANIM_TICK_SECS" 'BEGIN{r=a/b; print (r<1)?1:int(r+0.5)}')

have() { command -v "$1" >/dev/null 2>&1; }

NET_IFACE=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
[ -z "${NET_IFACE:-}" ] && NET_IFACE=$(ls /sys/class/net 2>/dev/null | grep -v '^lo$' | head -1)

get_gpu() {
    if have nvidia-smi; then
        nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw \
            --format=csv,noheader,nounits 2>/dev/null | \
            awk -F', ' '{printf "%s%%  %s°C  %s/%sMiB  %sW", $1, $2, $3, $4, $5}'
    else
        printf "N/A (no nvidia-smi)"
    fi
}

get_cpu_temp() {
    local val
    if have sensors; then
        val=$(sensors 2>/dev/null | awk '
            /^Package id 0:/ {print $4; exit}
            /^Tctl:/         {print $2; exit}
            /^Tdie:/         {print $2; exit}
            /^Core 0:/       {print $3; exit}
            /^temp1:/        {print $2; exit}
        ')
        [ -n "$val" ] && { printf "%s" "$val"; return; }
    fi
    if [ -r /sys/class/thermal/thermal_zone0/temp ]; then
        awk '{printf "+%.1f°C", $1/1000}' /sys/class/thermal/thermal_zone0/temp
        return
    fi
    printf "N/A"
}

get_battery() {
    local bat info pct state full full_design health
    bat=$(have upower && upower -e 2>/dev/null | grep -i 'BAT' | head -1)
    if [ -z "${bat:-}" ]; then
        printf "No battery"
        return
    fi
    info=$(upower -i "$bat" 2>/dev/null)
    pct=$(awk -F': *' '/percentage:/ {print $2; exit}' <<<"$info")
    state=$(awk -F': *' '/state:/ {print $2; exit}' <<<"$info")
    full=$(awk -F': *' '/energy-full:/ {print $2; exit}' <<<"$info" | awk '{print $1}')
    full_design=$(awk -F': *' '/energy-full-design:/ {print $2; exit}' <<<"$info" | awk '{print $1}')
    if [ -n "${full:-}" ] && [ -n "${full_design:-}" ]; then
        health=$(awk -v f="$full" -v fd="$full_design" 'BEGIN{ if (fd>0) printf "%.1f%%", (f/fd)*100; else print "N/A" }')
    else
        health="N/A"
    fi
    printf "%s (%s) — health %s" "${pct:-?}" "${state:-?}" "$health"
}

get_disk() {
    df -h --output=used,size,pcent / 2>/dev/null | awk 'NR==2{printf "%s / %s (%s)", $1, $2, $3}'
}

PREV_RX=0
PREV_TX=0
NET_INIT=0
init_net() {
    local rxf="/sys/class/net/${NET_IFACE}/statistics/rx_bytes"
    local txf="/sys/class/net/${NET_IFACE}/statistics/tx_bytes"
    if [ -r "$rxf" ] && [ -r "$txf" ]; then
        PREV_RX=$(cat "$rxf")
        PREV_TX=$(cat "$txf")
    fi
}
get_net() {
    local rxf="/sys/class/net/${NET_IFACE}/statistics/rx_bytes"
    local txf="/sys/class/net/${NET_IFACE}/statistics/tx_bytes"
    if [ -z "${NET_IFACE:-}" ] || [ ! -r "$rxf" ]; then
        printf "N/A"
        return
    fi
    if [ "$NET_INIT" -eq 0 ]; then
        NET_INIT=1
        printf "measuring…"
        return
    fi
    local now_rx now_tx d_rx d_tx
    now_rx=$(cat "$rxf")
    now_tx=$(cat "$txf")
    d_rx=$(( now_rx - PREV_RX ))
    d_tx=$(( now_tx - PREV_TX ))
    PREV_RX=$now_rx
    PREV_TX=$now_tx
    (( d_rx < 0 )) && d_rx=0
    (( d_tx < 0 )) && d_tx=0
    awk -v r="$d_rx" -v t="$d_tx" -v ivl="$STAT_REFRESH_SECS" \
        'BEGIN{ printf "↓ %.1f KB/s  ↑ %.1f KB/s", (r/ivl)/1024, (t/ivl)/1024 }'
}

get_media() {
    if ! have playerctl; then
        printf "playerctl not found"
        return
    fi
    local status artist title
    status=$(playerctl status 2>/dev/null)
    if [ -z "$status" ]; then
        printf "Nothing playing"
        return
    fi
    artist=$(playerctl metadata artist 2>/dev/null)
    title=$(playerctl metadata title 2>/dev/null)
    printf "%s — %s [%s]" "${title:-Unknown title}" "${artist:-Unknown artist}" "$status"
}

LOGO=(
"    ▄▄▄▄▄▄▄▄▄▄▄▄    "
"  ▄██▀▀▀▀▀▀▀▀▀▀██▄  "
" ██▀   ██    ██   ▀██ "
" ██    ██    ██    ██ "
" ██    ██████████    ██ "
" ██    ██    ██    ██ "
" ▀██▄            ▄██▀ "
"    ▀▀▀▀▀▀▀▀▀▀▀▀    "
)
FRAME_COUNT=${#LOGO[@]}

cleanup() {
    tput cnorm 2>/dev/null
    tput sgr0 2>/dev/null
    clear
    exit 0
}
trap cleanup INT TERM

render() {
    local frame=$1
    local host user sep
    host=$(hostname)
    user=$(whoami)
    sep=$(printf '%.0s―' {1..28})

    local INFO=(
        "${BOLD}${ACCENT}${user}${RESET}${DIM}@${RESET}${BOLD}${ACCENT}${host}${RESET}"
        "${DIM}${sep}${RESET}"
        "${BOLD}${ACCENT2}GPU${RESET}       ${GPU}"
        "${BOLD}${ACCENT2}CPU Temp${RESET}  ${CPUTEMP}"
        "${BOLD}${ACCENT2}Battery${RESET}   ${BATTERY}"
        "${BOLD}${ACCENT2}Disk${RESET}      ${DISK}"
        "${BOLD}${ACCENT2}Net${RESET}       ${NET} (${NET_IFACE:-?})"
        "${BOLD}${ACCENT2}Media${RESET}     ${MEDIA}"
    )

    tput cup 0 0
    local i line color
    for i in "${!LOGO[@]}"; do
        if [ "$i" -eq "$frame" ]; then
            color="${BOLD}${ACCENT}"
        else
            color="${DIM}"
        fi
        printf "%b%-22s%b  %b\n" "$color" "${LOGO[$i]}" "$RESET" "${INFO[$i]:-}"
    done
    tput ed
}

clear
tput civis 2>/dev/null
init_net

GPU=$(get_gpu)
CPUTEMP=$(get_cpu_temp)
BATTERY=$(get_battery)
DISK=$(get_disk)
NET=$(get_net)
MEDIA=$(get_media)

tick=0
frame=0
while true; do
    if (( tick % TICKS_PER_REFRESH == 0 )); then
        GPU=$(get_gpu)
        CPUTEMP=$(get_cpu_temp)
        BATTERY=$(get_battery)
        DISK=$(get_disk)
        NET=$(get_net)
        MEDIA=$(get_media)
    fi

    render "$frame"

    frame=$(( (frame + 1) % FRAME_COUNT ))
    tick=$(( tick + 1 ))

    read -rsn1 -t "$ANIM_TICK_SECS" key && [[ "$key" == "q" ]] && cleanup
done
