# Twelve Parser

Een script dat ruwe transactiegegevens uit Twelve haalt en daarvan een
importbestand voor facturen in Exact maakt.

## Limitaties

Het script werkt, maar het weet niet wat er is aangepast in Twelve. Dus als er
nieuwe producten zijn, de inkoopproductprijs is aangepast, of als er nieuwe "no
sale" mogelijkheden zijn bijgekomen, dan moeten het script, Twelve en Exact
aangepast worden!

## Gebruik

Zorg dat je nooit handmatig de transactiegegevens uit Twelve haalt!

Belangrijk om te lezen voor gebruik:

- Exporteer transactiegegevens (Rapportage > Overige > Basisgegevens > Deze
  lijst naar csv) NB: pak de goede begin- en einddatum!
- Zorg dat alle artikelen in Exact aanwezig zijn met de juiste btw-code en
  inkoopprijs
- Importeer het `facturen.csv` bestand via Import/Export > CSV/Excel >
  Verkoopfacturen (import) > Mijn importdefinities > Import script
- Voeg na afloop een duidelijke Uw. Ref. in bij externe borrels en borrels van
  de VvTP (zo weten de respectieve penningmeesters waar de factuur om gaat)
- Als je naar de TU factureert, zorg dan dat de juiste contactpersoon in Exact
  staat, en dat bij het veld BSN/sofinummer de baancode is ingevuld. Dit wordt
  in de factuurlayout voor de TU gebruikt. Als het niet is ingevuld, wordt de
  factuur niet betaald.
- Controleer de facturen voor gebruik (vooral die voor de VvTP en externe
  instanties) en verstuur ze in Exact via email.
- Letter 9998: Kassa intern af (zie hieronder)

Na afloop krijg je een bestand `facturen.csv` die je kan importeren in Exact.
Alle PIN transacties gaan via de relatie "Kassadebiteur", en die letteren
precies goed af op het bedrag dat via de PIN is binnengekomen. Interne
transacties gaan via de relatie "Kassa intern", deze moet je nog afletteren op
de juiste grootboekkaarten "representatie" en "gebruik tappers". Doe dit door
te gaan naar 9998: Kassa intern > afletteren, en selecteer eerst alle
transacties met "gebruik tappers", druk op afletteren. Druk op "overige", vul
de juiste grootboekrekening in, een goede omschrijving, boekdatum in de juiste
periode, en druk op afletteren. Doe hetzelfde voor "representatie" of andere
openstaande transacties.

## Extern gebruik

Het script is gemaakt voor intern gebruik voor de Vereniging voor Technische
Physica, dus als je het als externe wilt gebruiken moet je hoogstwaarschijnlijk
veel aanpassen om het werkend te krijgen.

## Foutmeldingen

Er kunnen foutmeldingen optreden, die meestal onder de volgende categorieën
vallen: fouten bij het runnen van het script, of fouten bij de Exact import.

- Er is een nieuwe "no-sale" mogelijkheid aangemaakt in Twelve of de spelling
  is aangepast.
  - Als de categorie is hernoemd, dan pas dit aan in het script en maak een
    pull request aan. In `export_ruwe_transactiegegevens.csv` moet
    waarschijnlijk de oude naam vervangen worden, aangezien de naam halverwege
    is veranderd.
  - Als er een nieuwe "no-sale" mogelijkheid is bijgekomen, dan moet de logica
    in het script worden herschreven. Vooral de functions `add_customer` en
    `add_description` zijn hiervoor van belang. Vraag om hulp!
- Er zijn artikelen in Twelve aanwezig maar niet in Exact. Maak die aan in
  Exact door een oud artikel (en voorraad GBR) te kopieren (en aan te passen)
  en probeer het bestand opnieuw te importeren.
