// Check-up de la carte support Table d'Eveil (v1.4)
// Televerse, ouvre le moniteur serie a 115200 bauds, puis touche chaque commande.
// Carte : "ESP32 Dev Module" (core Arduino ESP32 3.x).

struct Entree { uint8_t pin; const char *nom; };

const Entree BOUTONS[] = {
  {13, "Piano 1"}, {14, "Piano 2"}, {27, "Piano 3"}, {32, "Piano 4"},
  {18, "Forme 1"}, {19, "Forme 2"}, {21, "Forme 3"},
  {26, "Maracas"}, {25, "Trappe"},  {23, "Bongo"},
  {33, "Guitare 1"}, {39, "Guitare 2"},
  {15, "Livre"},
  {36, "SW1 MIDI/HID"},
  {5,  "Bouton D5 (carte)"},
};
const uint8_t NB = sizeof(BOUTONS) / sizeof(BOUTONS[0]);

const uint8_t PIN_SW2 = 35, PIN_SLIDER = 34, PIN_HP = 12, PIN_LED_ETAT = 2;
const uint8_t PIN_LED[4] = {22, 4, 16, 17};

bool etat[NB], vu[NB];
uint32_t dernierChangement[NB];
int dernierLayer = -1, dernierSlider = -1000;

void bip(int freq, int ms) { tone(PIN_HP, freq, ms); }

int lireLayer(int &brut) {
  brut = analogRead(PIN_SW2);
  if (brut < 1000) return 0;   // position A
  if (brut < 3000) return 2;   // position C
  return 1;                    // centre
}

void resteATester() {
  Serial.print("Reste a tester :");
  bool aucun = true;
  for (uint8_t i = 0; i < NB; i++)
    if (!vu[i]) { Serial.printf(" [%s]", BOUTONS[i].nom); aucun = false; }
  Serial.println(aucun ? " rien, tous les boutons repondent !" : "");
}

void setup() {
  Serial.begin(115200);
  delay(800);
  Serial.println("\n=== CHECK-UP TABLE D'EVEIL ===");

  pinMode(PIN_LED_ETAT, OUTPUT);
  for (uint8_t i = 0; i < 4; i++) pinMode(PIN_LED[i], OUTPUT);
  for (uint8_t i = 0; i < NB; i++)
    pinMode(BOUTONS[i].pin, BOUTONS[i].pin >= 34 ? INPUT : INPUT_PULLUP);
  delay(50);

  // 1. Entrees deja a la masse au demarrage = court-circuit ou bouton coince
  Serial.println("\n[1] Entrees au repos (doivent etre HAUT)");
  bool ok = true;
  for (uint8_t i = 0; i < NB; i++) {
    etat[i] = digitalRead(BOUTONS[i].pin) == LOW;
    if (etat[i]) {
      ok = false;
      Serial.printf("  !! %s (GPIO %d) lit BAS sans appui : court-circuit, fil inverse ou",
                    BOUTONS[i].nom, BOUTONS[i].pin);
      Serial.println(BOUTONS[i].pin == 36 ? " SW1 simplement en position basse" : " bouton maintenu");
    }
  }
  if (ok) Serial.println("  OK, aucune entree bloquee");

  // 2. Sorties : LED d'etat, LED 1-4, haut-parleur
  Serial.println("\n[2] Sorties : LED d'etat, chenillard LED 1-4, gamme au haut-parleur");
  for (uint8_t k = 0; k < 2; k++) {
    for (uint8_t i = 0; i < 4; i++) {
      digitalWrite(PIN_LED_ETAT, HIGH); digitalWrite(PIN_LED[i], HIGH);
      bip(440 + 110 * i, 120); delay(150);
      digitalWrite(PIN_LED_ETAT, LOW); digitalWrite(PIN_LED[i], LOW);
    }
  }
  Serial.println("  As-tu vu la LED d'etat clignoter et entendu 8 bips ?");

  // 3. Analogique
  int brut;
  dernierLayer = lireLayer(brut);
  Serial.printf("\n[3] SW2 : layer %d (valeur %d)  |  Slider : %d %%\n",
                dernierLayer, brut, analogRead(PIN_SLIDER) * 100 / 4095);

  Serial.println("\n[4] Appuie sur chaque bouton, bouge SW1, SW2 et le slider.");
  Serial.println("    Tape 'r' dans le moniteur pour la liste de ce qui reste a tester.\n");
  resteATester();
}

void loop() {
  uint32_t t = millis();
  bool unAppui = false;

  for (uint8_t i = 0; i < NB; i++) {
    bool bas = digitalRead(BOUTONS[i].pin) == LOW;
    if (bas != etat[i] && t - dernierChangement[i] > 30) {   // anti-rebond
      etat[i] = bas;
      dernierChangement[i] = t;
      Serial.printf("%-18s GPIO %2d  %s\n", BOUTONS[i].nom, BOUTONS[i].pin,
                    bas ? "APPUYE" : "relache");
      if (bas) {
        bip(300 + 60 * i, 80);
        if (!vu[i]) { vu[i] = true; resteATester(); }
      }
    }
    unAppui |= etat[i] && BOUTONS[i].pin != 36;   // SW1 est un interrupteur
  }
  digitalWrite(PIN_LED_ETAT, unAppui);

  int brut, layer = lireLayer(brut);
  if (layer != dernierLayer) {
    dernierLayer = layer;
    Serial.printf("SW2                layer %d (valeur %d)\n", layer, brut);
  }

  int s = analogRead(PIN_SLIDER);
  if (abs(s - dernierSlider) > 80) {
    dernierSlider = s;
    Serial.printf("Slider             %3d %%  (valeur %d)\n", s * 100 / 4095, s);
  }

  if (Serial.available() && Serial.read() == 'r') resteATester();
  delay(5);
}
