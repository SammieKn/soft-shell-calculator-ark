# Overdrachtsbrief broncode Soft-shell calculator 2025 v1.1 aan gemeente

Deze brief dient als begeleidend document bij de overdracht van de broncode van de ‘Soft-shell calculator 2025-v1.1’ naar de Gemeente Amsterdam.

## Achtergrond van de Soft-shell calculator

De doelstelling van de opdracht met betrekking tot het onderzoek naar de potentie van de RPD (ResiPowerDrill, micro-boringen) als meetinstrument voor de beoordeling van houten palen in situ is geformuleerd in de opdrachtbeschrijving:  
‘Beoordelen van de geschiktheid van RPD boringen in situ onder water met betrekking tot lokale degradatie/aantasting en de houtkwaliteit voor inspectiedoeleinden, zodat het nemen van boormonsters overbodig wordt.’

De resultaten van deze onderzoeken zijn vastgelegd in diverse rapporten.

Onder de geformuleerde werkzaamheden behoorde het analyseren van RPD metingen met betrekking tot het identificeren van de “zachte schil”, waar ernstige degradatie aanwezig is.

Versie 1.1 bevat een verbeterde nauwkeurigheid in de bepaling van de paaldiameter en de zachte schil aan de uitgangszijde van het RPD-signaal, zoals vastgelegd in de achtergrondrapporten. Tevens bevat versie 1.1 een schatting van de verhouding tussen spinthout en kernhout in de paal. Ook is de visuele weergave van de resultaten en de uitvoer in Excel- en PDF-bestanden verbeterd.

## Soft-shell calculator

In het kader van het analyseren van de RPD-metingen is een eerste versie van een Python-routine geschreven voor intern gebruik, om de metingen van de RPD beter te kunnen analyseren en sneller informatie uit grotere datasets te verkrijgen. Een voordeel van deze routine is dat deze ook een visuele beoordeling van het RPD-signaal geeft. Deze versie is in overleg met de gemeente Amsterdam beschikbaar gesteld. De gemeente heeft daarna opdracht gegeven de routine uit te breiden met de onderwerpen genoemd in de achtergrond-paragraaf.

De verbeterde routine, genaamd “Soft-shell calculator 2025-v1.1”, is reeds als ‘executable’ aan Amsterdam beschikbaar gesteld, zodat ervaring kan worden opgedaan met de beoordeling van signalen, in het bijzonder bij het beoordelen van de kwaliteit van RPD-signalen van in-situ metingen. Daarbij is ook een handleiding opgeleverd, waarin wordt uitgelegd hoe met de routine gewerkt kan worden. Daarin is specifiek aangegeven dat dit een onderzoeksversie is.

### Disclaimer

> Deze tool is met zo groot mogelijke zorgvuldigheid ontwikkeld, maar het is niet uitgesloten dat er fouten of onvolkomenheden in de software zitten.  
> De tool is expliciet bedoeld als experimentele versie voor intern gebruik bij de Gemeente Amsterdam om ervaring op te doen met de interpretatie van RPD-signalen.  
> Het is geen commerciële versie en er is geen intentie om deze tool als commerciële versie te onderhouden. Een dergelijke versie kan eventueel in een later stadium met een professionele softwareontwikkelaar verder geprogrammeerd en onderhouden worden.  
> De Soft-shell calculator kan alleen een betrouwbare waarde voor de zachte schil afgeven als het signaal van voldoende kwaliteit is. Dit vergt ervaring van de gebruiker om dit te beoordelen.

De executable is niet bedoeld om direct door constructeurs zelfstandig gebruikt te worden. De sectie die verantwoordelijk is voor deze tool is geen professionele softwareontwikkelaar, en kan derhalve niet garanderen dat er geen fouten in de software zitten, of anticiperen op verkeerde invoer of interpretatie van de uitkomsten en RPD-signalen. Het staat Amsterdam vrij om met de aangeleverde broncode een geschikte versie voor ingenieurs te maken, mits de originele auteur als bron wordt vermeld. De ontwikkelende partij is niet verantwoordelijk voor de ontwikkeling en werking van deze versies, maar is bereid om Amsterdam op projectbasis aan verdere ontwikkelingen bij te dragen.

In de bijgevoegde zipfile “Soft_shell_calc_2025_v1.1” is de broncode van de applicatie opgenomen.

Met vriendelijke groet,

[Ondertekenaars verwijderd]