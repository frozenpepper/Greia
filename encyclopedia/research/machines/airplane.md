# Airplane — v0.1 research authority

**Page ID:** `machines.airplane`  
**Presenter:** Flash (`greia.flash.v1`)  
**Primary sources:**
- NASA Glenn Research Center — What Is Lift?: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/what-is-lift/
- NASA Glenn Research Center — Four Forces on an Airplane: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/four-forces-on-an-airplane/
- NASA Glenn Research Center — Bernoulli and Newton: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/bernoulli-and-newton/
- NASA Glenn Research Center — Incorrect Lift Theory: https://www.grc.nasa.gov/WWW/k-12/VirtualAero/BottleRocket/airplane/wrong1.html

**Research state:** READY FOR AUTHORING

## Accepted claims

### Wings make aerodynamic lift by interacting with moving air

Lift is a mechanical force created when a wing interacts with air moving relative to it. Pressure differences around the wing and the turning of airflow are two consistent ways to describe the same aerodynamic result. Both upper and lower wing surfaces matter.

### There is no required equal transit time

Air separated at a wing's leading edge does not need to reunite at the trailing edge at the same time. The common story that air on top “must go faster because it has farther to travel” is explicitly incorrect and must never appear in narration or visuals.

### Four forces matter

An airplane in flight is acted on by lift, weight, thrust and drag. In steady level cruise these can be balanced approximately: lift balances weight and thrust balances drag. When they are unbalanced, the airplane's motion changes.

### Thrust moves the airplane through air; wings provide lift

Engines/propellers provide thrust, not the primary lifting force in ordinary wing-borne flight. Gliders show that wings can generate lift without an engine once there is suitable motion through air.

## Scope guardrails

- Never use the false equal-transit-time explanation.
- Do not say Bernoulli or Newton “alone” is the one true explanation of lift; avoid the fake either/or.
- Do not imply an engine directly holds an ordinary airplane up; thrust moves it through the air while wings generate lift.
- Airflow lines are schematic; do not claim exact streamline shape or pressure magnitude.
- Keep stall/aerodynamic limits outside v0.1 unless later researched as a dedicated topic.
- No flight-control simulation complexity; this is a child-scale force/airflow demonstration.

## Interaction → fact mapping

| interaction | factual purpose |
|---|---|
| turn on airflow past wing | relative air motion is required for aerodynamic lift |
| change wing angle modestly | wing orientation changes how airflow/forces behave |
| four-force reveal | lift/weight/thrust/drag act in different directions |
| thrust toggle | thrust moves airplane forward through air; it is not the same force as lift |

## Approved narration wording

### `encyclopedia.machines.airplane.intro`

**it:** Pronti al decollo! Un aereo vola grazie a diverse forze che lavorano insieme. Le ali interagiscono con l'aria in movimento e producono portanza, mentre il motore o l'elica forniscono spinta.

**en:** Ready for takeoff! An airplane flies because several forces work together. Its wings interact with moving air to produce lift, while an engine or propeller provides thrust.

### `encyclopedia.machines.airplane.lift`

**it:** Quando l'aria scorre intorno a un'ala, l'ala cambia il movimento dell'aria e si crea una distribuzione di pressione che produce una forza verso l'alto: la portanza.

**en:** When air flows around a wing, the wing changes the motion of the air and creates a pressure pattern that produces an upward force: lift.

### `encyclopedia.machines.airplane.myth`

**it:** Una cosa importante: l'aria che passa sopra e sotto l'ala non deve ritrovarsi nello stesso momento dietro l'ala. La famosa storia del percorso più lungo non spiega correttamente la portanza.

**en:** One important thing: air passing above and below a wing does not have to meet again at the same time behind it. The famous longer-path story does not correctly explain lift.

### `encyclopedia.machines.airplane.forces`

**it:** In volo agiscono quattro forze principali: portanza verso l'alto, peso verso il basso, spinta in avanti e resistenza dell'aria all'indietro. Se cambiano, cambia anche il movimento dell'aereo.

**en:** Four main forces act in flight: lift upward, weight downward, thrust forward, and drag backward. When their balance changes, the airplane's motion changes too.

### `encyclopedia.machines.airplane.thrust`

**it:** Il motore o l'elica spingono l'aereo in avanti attraverso l'aria. Le ali fanno il lavoro principale di portanza: infatti anche un aliante senza motore può volare mentre si muove nell'aria.

**en:** An engine or propeller pushes the airplane forward through the air. The wings do the main lifting work; even an engine-free glider can fly while it moves through the air.
