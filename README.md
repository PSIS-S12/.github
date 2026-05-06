# Navodila za izboljšavo PRIMAL2 glede na pristope opisane v drugih člankih

## Nadgradnje za PRIMAL2

### Glede na Conformant-CBS
* **Osnovna ideja**: Vpeljava časovne negotovosti v načrtovanje poti, da postanejo agenti bolj robustni na nepredvidene zamude.
* **Zbiranje podatkov**: Med treningom beležimo dejanske čase prehodov čez robove mape in izračunamo minimalni (L) in maksimalni (U) čas prehodov.
* **Določitev časovnih meja**: Na podlagi vzorcev se določi zgornja meja trajanja akcije (premik ali čakanje), ki služi kot pesimistična ocena (SOC_pes).
* **Posodobitev modula A***: Pri A* (Path Length Map) uporabimo naučene pesimistične meje [L, U] namesto fiksne cene koraka.
* **Izboljšava**: Zemljevid dolžine poti usmerja agenta bolj previdno z upoštevanjem "potencialne prisotnosti" sosedov, kar zmanjšuje tveganje za zastoje (deadlocke).

---

### Glede na Guided-PIBT
* **Osnovna ideja**: Uporaba časovno neodvisnih vodičevih poti (guide paths), ki vnaprej upoštevajo pričakovano zgostitev prometa.
* **Modeliranje prometa**: Definiramo strošek vozlišča na podlagi števila agentov, ki vanj vstopajo (pv), in strošek nasprotnega toka (ce) za preprečevanje zastojev v hodnikih.
* **Vodičeva hevristika**: Namesto proste razdalje do cilja izračunamo hi(v) kot kombinacijo razdalje do vodičeve poti (dp) in preostale poti do cilja po tej poti (dg).
* **Spletno izboljševanje (Refinement)**: Vsak časovni korak naključno izberemo podmnožico agentov in posodobimo njihove vodičeve poti glede na trenutne realne pretoke.
* **Izboljšava**: Agenti prejmejo informacijo o globalno manj obremenjenih poteh, kar poveča skupni pretok (throughput) in zmanjša konflikte na kritičnih točkah.
