"""Etapes de routage : export DSN, import SES, plans de masse, DRC.

python3 route.py export   -> table_eveil.dsn
python3 route.py import   -> importe table_eveil.ses, coule les plans GND, DRC
"""
import sys
import pcbnew
from pcbnew import VECTOR2I_MM as P, FromMM

PCB = "table_eveil.kicad_pcb"
OX, OY, W, H = 100.0, 100.0, 70.0, 70.0

board = pcbnew.LoadBoard(PCB)

if sys.argv[1] == "export":
    # Freerouting ne doit pas router GND : il passe par les plans de masse,
    # mais on le laisse router quand meme pour garantir la continuite.
    ok = pcbnew.ExportSpecctraDSN(board, "table_eveil.dsn")
    print("dsn:", ok)
    sys.exit(0)



def import_ses(path):
    """Lecteur SES minimal (KiCad 7 n'expose pas l'import en Python)."""
    import re
    toks = re.findall(r'\(|\)|"[^"]*"|[^\s()]+', open(path).read())
    pos = 0

    def parse():
        nonlocal pos
        out = []
        while pos < len(toks):
            t = toks[pos]; pos += 1
            if t == "(":
                out.append(parse())
            elif t == ")":
                return out
            else:
                out.append(t.strip('"'))
        return out

    tree = parse()[0]
    to_mm = lambda v: int(v) / 10000.0
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    routes = next(n for n in tree if isinstance(n, list) and n[0] == "routes")
    netw = next(n for n in routes if isinstance(n, list) and n[0] == "network_out")
    tracks = vias = 0
    for netnode in netw[1:]:
        net = board.FindNet(netnode[1])
        for item in netnode[2:]:
            if item[0] == "wire":
                path = item[1]
                layer, width = layers[path[1]], to_mm(path[2])
                pts = [(to_mm(path[i]), -to_mm(path[i + 1])) for i in range(3, len(path) - 1, 2)]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2))
                    t.SetWidth(FromMM(width)); t.SetLayer(layer); t.SetNet(net)
                    board.Add(t); tracks += 1
            elif item[0] == "via":
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(P(to_mm(item[2]), -to_mm(item[3])))
                v.SetWidth(FromMM(0.8)); v.SetDrill(FromMM(0.4))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net)
                board.Add(v); vias += 1
    print("pistes:", tracks, "vias:", vias)


import_ses("table_eveil.ses")

gnd = board.FindNet("GND")
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetLocalClearance(FromMM(0.3))
    z.SetMinThickness(FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(FromMM(0.4))
    z.SetThermalReliefSpokeWidth(FromMM(0.5))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
        ol.Append(FromMM(OX + x), FromMM(OY + y))
    board.Add(z)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
pcbnew.WriteDRCReport(board, "drc.rpt", pcbnew.EDA_UNITS_MILLIMETRES, True)
print(open("drc.rpt").read()[-1500:])
