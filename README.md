# Navodila za izboljšavo PRIMAL2 glede na pristope opisane v drugih člankih

## Nadgradnje za PRIMAL2

### Glede na Conformant-CBS
**Osnovna ideja:** Vpeljava časovne negotovosti v načrtovanje poti, da postanejo agenti bolj robustni na nepredvidene zamude.

1.  **Zbiranje podatkov:** Med treningom (agentov) beležimo dejanske čase prehodov čez robove mape (mapa je mreža, zato so robovi) in izračunamo minimalni ($L$ - Lower bound) in maksimalni ($U$ - Upper bound) čas.

2.  **Določitev časovnih meja:** Na podlagi vzorcev (pridobljeni pri učenju) se določi zgornja meja trajanja akcije (diskreten premik v eno smer ali čakanje na mestu), ki služi kot pesimistična ocena (najdaljši zabeležen čas za dokončanje premika/čakanja).

3. **Posodobitev modula $A^{*}$:** Pri $A^{*}$ (ki ga $PRIMAL_{2}$ uporablja za zemljevid najkrajše poti in predvidevanje sosedov) uporabimo naučene pesimistične meje ($[L, U]$) namesto fiksne cene koraka.

**Izboljšava:** Tak zemljevid dolžine poti agenta usmerja bolj previdno, saj upošteva možnost zamud sosednjih agentov (koncept potencialne prisotnosti). S tem zmanjšuje tveganje za zastoje (deadlocke) v primerjavi z originalno implementacijo.

---

### Glede na Guided-PIBT
* **Osnovna ideja**: Uporaba časovno neodvisnih vodičevih poti (guide paths), ki vnaprej upoštevajo pričakovano zgostitev prometa.

* **Izboljšava**: Agenti prejmejo informacijo o globalno manj obremenjenih poteh, kar poveča skupni pretok (throughput) in zmanjša konflikte na kritičnih točkah.
