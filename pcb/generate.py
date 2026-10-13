"""Genere la carte support ESP32 DevKit V1 de la table d'eveil (KiCad 7).

Usage : python3 generate.py   -> table_eveil.kicad_pcb (non route)
Le routage est fait ensuite par build.sh (Freerouting), puis route.py.
"""
import pcbnew
from pcbnew import VECTOR2I_MM as P, FromMM

FP = "/usr/share/kicad/footprints"

# ---- geometrie (mm, origine = coin haut-gauche de la carte) ----
OX, OY = 100.0, 100.0           # decalage dans la feuille KiCad
W = H = 70.0                    # taille de la carte
HOLE_SPACING = 49.0             # entraxe des 4 trous (carre)
HOLE_FP = "MountingHole_3.2mm_M3"

SOCK_L_X, SOCK_R_X = 35.0 - 12.7, 35.0 + 12.7   # rangees DevKit, 25,4 mm
SOCK_Y0 = 28.1                  # broche 1 (EN / D23), USB vers le bas

# DevKit V1 30 broches, vue de dessus, antenne en haut
LEFT = ["EN", "VP36", "VN39", "IO34", "IO35", "IO32", "IO33", "IO25",
        "IO26", "IO27", "IO14", "IO12", "IO13", "GND", "VIN"]
RIGHT = ["IO23", "IO22", "TX0", "RX0", "IO21", "IO19", "IO18", "IO5",
         "IO17", "IO16", "IO4", "IO2", "IO15", "GND", "3V3"]

board = pcbnew.BOARD()
nets = {}


def net(name):
    if name is None:
        return None
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


def place(lib, name, ref, value, x, y, rot=0, pads=None, show_ref=True):
    fp = pcbnew.FootprintLoad(f"{FP}/{lib}.pretty", name)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(P(OX + x, OY + y))
    if rot:
        fp.SetOrientationDegrees(rot)
    board.Add(fp)
    fp.Value().SetVisible(False)
    fp.Reference().SetVisible(show_ref)
    fp.Reference().SetTextSize(P(0.8, 0.8))
    fp.Reference().SetTextThickness(FromMM(0.12))
    for pad in fp.Pads():
        n = (pads or {}).get(pad.GetNumber())
        if n:
            pad.SetNet(net(n))
    return fp


def text(s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0, just=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(P(OX + x, OY + y))
    t.SetLayer(layer)
    t.SetTextSize(P(size, size))
    t.SetTextThickness(FromMM(max(0.12, size * 0.15)))
    if rot:
        t.SetTextAngleDegrees(rot)
    if just < 0:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    elif just > 0:
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    board.Add(t)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    return t


def seg(x1, y1, x2, y2, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(OX + x1, OY + y1))
    s.SetEnd(P(OX + x2, OY + y2))
    s.SetLayer(layer)
    s.SetWidth(FromMM(w))
    board.Add(s)


# ---- regles (compatibles JLCPCB / PCBWay / Aisler) ----
ds = board.GetDesignSettings()
ds.m_TrackMinWidth = FromMM(0.25)
ds.m_MinClearance = FromMM(0.2)
ds.m_ViasMinSize = FromMM(0.6)
ds.m_MinThroughDrill = FromMM(0.3)
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetTrackWidth(FromMM(0.4))
nc.SetClearance(FromMM(0.25))
nc.SetViaDiameter(FromMM(0.8))
nc.SetViaDrill(FromMM(0.4))

# ---- contour ----
seg(0, 0, W, 0); seg(W, 0, W, H); seg(W, H, 0, H); seg(0, H, 0, 0)

# ---- trous de fixation ----
c = W / 2
for i, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
    place("MountingHole", HOLE_FP, f"H{i+1}", "M3",
          c + dx * HOLE_SPACING / 2, c + dy * HOLE_SPACING / 2, show_ref=False)

# ---- supports DevKit ----
def gpio_net(label):
    return {"VIN": "+5V", "3V3": "+3V3", "GND": "GND",
            "TX0": None, "RX0": None}.get(label, label)

place("Connector_PinSocket_2.54mm", "PinSocket_1x15_P2.54mm_Vertical",
      "U1A", "DevKit gauche", SOCK_L_X, SOCK_Y0,
      pads={str(i + 1): gpio_net(n) for i, n in enumerate(LEFT)}, show_ref=False)
place("Connector_PinSocket_2.54mm", "PinSocket_1x15_P2.54mm_Vertical",
      "U1B", "DevKit droite", SOCK_R_X, SOCK_Y0,
      pads={str(i + 1): gpio_net(n) for i, n in enumerate(RIGHT)}, show_ref=False)

text("EN", SOCK_L_X + 1.6, SOCK_Y0, 0.9, just=-1)
text("D23", SOCK_R_X - 1.6, SOCK_Y0, 0.9, just=1)
text("ESP32 DevKit V1", 35, SOCK_Y0 - 3.0, 1.0)
text("USB", 35, 66.8, 1.2)
text("v", 35, 68.4, 1.2)

# ---- connecteurs des commandes : rangee signal + rangee GND ----
# gauche : impairs (exterieur) = GND, pairs (interieur) = signal
# droite : impairs (interieur) = signal, pairs (exterieur) = GND
STEP = 2.54
Y0 = 16.0
L_HDR_X = 3.0          # colonne GND gauche
R_HDR_X = W - 3.0 - STEP   # colonne signal droite

LEFT_GROUPS = [   # (ref, titre, position de depart, [(label, net)])
    ("J1", "GUITARE", 0, [("G1", "IO33"), ("G2", "VN39")]),
    ("J2", "TRAPPE", 3, [("TRAPPE", "IO25")]),
    ("J3", "MARACAS", 5, [("MARACAS", "IO26")]),
    ("J4", "PIANO", 7, [("P1", "IO13"), ("P2", "IO14"), ("P3", "IO27"), ("P4", "IO32")]),
    ("J5", "SW1", 12, [("MIDI/HID", "VP36")]),
    ("J6", "SW2", 14, [("A", "IO35"), ("C", "SW2_C")]),
]
RIGHT_GROUPS = [
    ("J7", "BONGO", 0, [("BONGO", "IO23")]),
    ("J8", "FORMES", 2, [("F1", "IO18"), ("F2", "IO19"), ("F3", "IO21")]),
    ("J9", "LIVRE", 6, [("LIVRE", "IO15")]),
    ("J10", "LED", 8, [("L1", "LED1"), ("L2", "LED2"), ("L3", "LED3"), ("L4", "LED4")]),
]


def header(ref, title, pos, sigs, side):
    n = len(sigs)
    y = Y0 + pos * STEP
    pads = {}
    for i, (_, s) in enumerate(sigs):
        odd, even = str(2 * i + 1), str(2 * i + 2)
        if side == "L":
            pads[odd], pads[even] = "GND", s
        else:
            pads[odd], pads[even] = s, "GND"
    x = L_HDR_X if side == "L" else R_HDR_X
    place("Connector_PinHeader_2.54mm", f"PinHeader_2x{n:02d}_P2.54mm_Vertical",
          ref, title, x, y, pads=pads, show_ref=False)
    for i, (lab, _) in enumerate(sigs):
        yy = y + i * STEP
        if side == "L":
            text(lab, L_HDR_X + STEP + 1.6, yy, 0.9, just=-1)
        else:
            text(lab, R_HDR_X - 1.6, yy, 0.9, just=1)
    # titre du groupe, a la verticale le long du bord
    ymid = y + (n - 1) * STEP / 2
    if n == 1:
        return
    if side == "L":
        text(title, 1.0, ymid, 0.8, rot=90)
    else:
        text(title, W - 1.0, ymid, 0.8, rot=90)


for g in LEFT_GROUPS:
    header(*g, side="L")
for g in RIGHT_GROUPS:
    header(*g, side="R")
text("GND", L_HDR_X, Y0 - 2.3, 0.8)
text("SIG", L_HDR_X + STEP, Y0 - 2.3, 0.8)
text("SIG", R_HDR_X, Y0 - 2.3, 0.8)
text("GND", R_HDR_X + STEP, Y0 - 2.3, 0.8)

# ---- bande du haut : boutons, LED d'etat, slider, haut-parleur ----
place("Button_Switch_THT", "SW_PUSH_6mm", "SW1", "RESET", 16.0, 3.0,
      pads={"1": "EN", "2": "GND"}, show_ref=False)
text("RESET", 19.25, 1.2, 0.9)
place("Button_Switch_THT", "SW_PUSH_6mm", "SW2", "BOUTON", 25.5, 3.0,
      pads={"1": "IO5", "2": "GND"}, show_ref=False)
text("BTN D5", 28.75, 1.2, 0.9)
place("LED_THT", "LED_D3.0mm", "D2", "LED etat", 35.5, 5.25,
      pads={"1": "GND", "2": "LED_ST"}, show_ref=False)
text("ETAT", 36.8, 1.2, 0.9)
place("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
      "J11", "SLIDER", 41.0, 6.25, rot=90,
      pads={"1": "+3V3", "2": "IO34", "3": "GND"}, show_ref=False)
text("SLIDER", 43.5, 1.2, 0.9)
text("3V3", 41.0, 8.3, 0.8); text("CUR", 43.54, 8.3, 0.8); text("GND", 46.08, 8.3, 0.8)
place("Connector_PinHeader_2.54mm", "PinHeader_1x02_P2.54mm_Vertical",
      "J12", "HAUT-PARLEUR", 50.0, 6.25, rot=90,
      pads={"1": "+5V", "2": "SPK_N"}, show_ref=False)
text("HP", 51.3, 1.2, 0.9)
text("+", 50.0, 8.3, 0.8); text("-", 52.54, 8.3, 0.8)

# ---- sous le DevKit : resistances, transistor, diode ----
R = ("Resistor_THT", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal")
CA, CB = 25.6, 36.7      # colonnes
row = lambda k: 31.0 + k * 3.0

RES = [  # ref, valeur, colonne, rangee, pad1, pad2
    ("R1", "10k", CA, 0, "+3V3", "VP36"),     # tirage SW1
    ("R2", "10k", CA, 1, "+3V3", "VN39"),     # tirage Guitare 2
    ("R3", "10k", CA, 2, "+3V3", "IO35"),     # tirage SW2
    ("R4", "10k", CA, 3, "SW2_C", "IO35"),    # echelle SW2, contact C
    ("R5", "1k", CA, 6, "IO12", "Q_B"),       # base transistor HP
    ("R6", "10k", CA, 7, "Q_B", "GND"),       # rappel base (GPIO12 bas au boot)
    ("R7", "47R 0.5W", CA, 9, "SPK_N", "Q_C"),  # limite le courant HP
    ("R8", "220R", CB, 0, "IO22", "LED1"),
    ("R9", "220R", CB, 1, "IO4", "LED2"),
    ("R10", "220R", CB, 2, "IO16", "LED3"),
    ("R11", "220R", CB, 3, "IO17", "LED4"),
    ("R12", "1k", CB, 5, "IO2", "LED_ST"),
]
for ref, val, x, k, a, b in RES:
    fp = place(*R, ref, val, x, row(k), pads={"1": a, "2": b})
    fp.Reference().SetPosition(P(OX + x + 3.81, OY + row(k)))
    fp.Reference().SetTextSize(P(0.9, 0.9))

# BC337 : 1 = C, 2 = B, 3 = E
place("Package_TO_SOT_THT", "TO-92_Inline_Wide", "Q1", "BC337", CB + 1.0, row(8) - 0.5,
      pads={"1": "Q_C", "2": "Q_B", "3": "GND"})
# diode de roue libre : cathode (1) au +5V, anode (2) cote transistor
place("Diode_THT", "D_DO-35_SOD27_P7.62mm_Horizontal", "D1", "1N4148", CB, row(10),
      pads={"1": "+5V", "2": "Q_C"})

# ---- pas de cuivre sous l'antenne du DevKit ----
ka = pcbnew.ZONE(board)
ka.SetIsRuleArea(True)
ka.SetDoNotAllowCopperPour(True)
ka.SetDoNotAllowTracks(True)
ka.SetDoNotAllowVias(True)
ka.SetDoNotAllowPads(False)
ka.SetDoNotAllowFootprints(False)
ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
ka.SetLayerSet(ls)
ol = ka.Outline()
ol.NewOutline()
for x, y in [(21.0, 14.5), (49.0, 14.5), (49.0, 26.0), (21.0, 26.0)]:
    ol.Append(FromMM(OX + x), FromMM(OY + y))
board.Add(ka)

# ---- marquage ----
text("TABLE D'EVEIL", 35, 13.2, 1.2)
text("carte support v1 - 2026", 35, 67.5, 0.8, layer=pcbnew.B_SilkS)

board.Save("table_eveil.kicad_pcb")
print("nets:", len(nets), "footprints:", len(board.GetFootprints()))
