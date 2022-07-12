# Twelve Parser

Een script dat ruwe transactiegegevens uit Twelve haalt en daarvan een
importbestand voor facturen in Exact maakt.

## Limitaties

Het script werkt, maar het weet niet wat er is aangepast in Twelve. Dus als er
nieuwe producten zijn, de inkoopproductprijs is aangepast, of als er nieuwe "no
sale" mogelijkheden zijn bijgekomen, dan moet het script aangepast worden!

## Gebruik

Zorg dat je nooit handmatig de transactiegegevens uit Twelve haalt!

Belangrijk om te lezen voor gebruik:

- Exporteer transactiegegevens (Rapportage > Overige > Basisgegevens > Deze
  lijst naar csv) NB: pak de goede begin- en einddatum!
- Zorg dat alle artikelen in Exact aanwezig zijn met de juiste btw-code en
  inkoopprijs
- Importeer het `facturen.csv` bestand via Import/Export > CSV/Excel >
  Verkoopfacturen (import) > Mijn importdefinities > Import script
- Importeer het `kassa_intern.csv` bestand via Import/Export > CSV/Excel >
  Verkoopboekingen (import) > Mijn importdefinities > Import script
- Voeg na afloop een duidelijke Uw. Ref. in bij externe borrels en borrels van
  de VvTP (zo weten de respectieve penningmeesters waar de factuur om gaat)

Na afloop krijg je een bestand `facturen.csv` en `kassa_intern.csv` die je kan
importeren in Exact. Alle PIN transacties gaan via de relatie "Kassadebiteur",
en die letteren precies goed af op het bedrag dat via de PIN is binnengekomen.
Interne transacties gaan via de relatie "Kassa intern", deze worden automatisch
afgeletterd op de juiste grootboekkaarten zoals "gebruik tappers" en "breuk &
bederf" als je dit bestand importeerd.

## Extern gebruik

Het script is gemaakt voor intern gebruik voor de Vereniging voor Technische
Physica, dus als je het als externe wilt gebruiken moet je hoogstwaarschijnlijk
veel aanpassen om het werkend te krijgen.
