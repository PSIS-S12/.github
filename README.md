# Navodila za izboljšavo PRIMAL2 glede na pristope opisane v drugih člankih

## Nadgradnje za PRIMAL2

### Glede na Conformant-CBS
**Osnovna ideja:** Vpeljava časovne negotovosti v načrtovanje poti, da postanejo agenti bolj robustni na nepredvidene zamude.

1.  **Zbiranje podatkov:** Med treningom (agentov) beležimo dejanske čase prehodov čez robove mape (mapa je mreža, zato so robovi) in izračunamo minimalni ($L$ - Lower bound) in maksimalni ($U$ - Upper bound) čas.

2.  **Določitev časovnih meja:** Na podlagi vzorcev (pridobljeni pri učenju) se določi zgornja meja trajanja akcije (diskreten premik v eno smer ali čakanje na mestu), ki služi kot pesimistična ocena (najdaljši zabeležen čas za dokončanje premika/čakanja).

3. **Posodobitev modula $A^{*}$:** Pri $A^{*}$ (ki ga $PRIMAL_{2}$ uporablja za zemljevid najkrajše poti in predvidevanje sosedov) uporabimo naučene pesimistične meje ($[L, U]$) namesto fiksne cene koraka.

**Izboljšava:** Tak zemljevid dolžine poti agenta usmerja bolj previdno, saj upošteva možnost zamud sosednjih agentov (koncept potencialne prisotnosti). S tem zmanjšuje tveganje za zastoje (deadlocke) v primerjavi z originalno implementacijo.

---

### Glede na learn-to-follow
**Osnovna ideja:** Agente naučimo, da se proaktivno izogibajo gneči tako, da si zapomnijo, kje so v preteklosti že videli druge agente.

1. **Beleženje gneče:** Vsak agent si sam vodi evidenco o tem, kolikokrat je na določenem kvadratku mape opazil druge sosede.
   
2. **Uporaba kazni za gnečo:** Pri načrtovanju poti kvadratkom, kjer je bila prej opažena gneča, dodelimo višji strošek. To deluje kot "kazen", ki agenta odvrača od prenatrpanih delov mape.

3. **Združevanje s časovno negotovostjo:** Skupni strošek poti izračunamo tako, da seštejemo pesimistični čas koraka (iz prejšnje nadgradnje - Conformant-CBS) in kazen za gnečo na tisti lokaciji.
   
4. **Osveževanje informacij:** Vsakič, ko agent opravi svojo trenutno nalogo in dobi nov cilj, pozabi preteklo gnečo in začne beležiti na novo. To prepreči, da bi ga stari podatki o prometu ovirali pri iskanju poti v trenutnih razmerah.

**Izboljšava:** Agenti se ne zgrnejo vsi na iste glavne poti, temveč se naravno razporedijo po celotnem skladišču. To prepreči nastanek ozkih grl in omogoča, da celotna skupina opravi več nalog v krajšem času.
