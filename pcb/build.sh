#!/bin/sh
# Regenere la carte de bout en bout : placement, routage, plans de masse,
# DRC, puis fichiers de fabrication dans fab/.
# Prerequis : KiCad 7 (pcbnew + kicad-cli), Java 17+, freerouting-1.9.0.jar
set -e
cd "$(dirname "$0")"
FREEROUTING=${FREEROUTING:-freerouting.jar}

python3 generate.py
python3 route.py export
rm -f table_eveil.ses
xvfb-run -a java -jar "$FREEROUTING" -de table_eveil.dsn -do table_eveil.ses -mp 60
python3 route.py import

rm -rf fab && mkdir -p fab/gerbers
kicad-cli pcb export gerbers --no-x2 --subtract-soldermask \
  --layers F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  -o fab/gerbers/ table_eveil.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-separate-th \
  --generate-map --map-format gerberx2 -o fab/gerbers/ table_eveil.kicad_pcb
(cd fab/gerbers && zip -q ../table_eveil_gerbers.zip *)
for L in F B; do
  kicad-cli pcb export svg --layers $L.Cu,$L.SilkS,$L.Mask,Edge.Cuts \
    --exclude-drawing-sheet --page-size-mode 2 -o fab/apercu_$L.svg table_eveil.kicad_pcb
done
kicad-cli pcb export pdf --layers F.SilkS,F.Fab,Edge.Cuts --black-and-white \
  -o fab/plan_montage.pdf table_eveil.kicad_pcb
echo "OK : fab/table_eveil_gerbers.zip"
