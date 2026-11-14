# Unfollow 0.3 • prototipo Android in italiano

L’utente collega il proprio profilo, analizza, inserisce eventuali nomi da proteggere e avvia una sola volta. Il motore percorre automaticamente i candidati mentre l’app rimane aperta. L’arresto richiesto durante un’operazione ha effetto prima della successiva. Serve una nuova scansione dopo un’interruzione. Il prototipo usa un client Instagram non ufficiale: la compatibilità con il servizio e il rischio di blocco restano da verificare. Nessuna frequenza è certificata da Meta. Non collegare un account che non puoi permetterti di perdere.

## Come compilare

Caricare il contenuto di questa cartella alla radice di un proprio repository, inclusa .github. Su GitHub aprire Actions → Unfollow Android → Run workflow. Una compilazione completata pubblica l’artefatto Unfollow-Android, contenente l’APK di debug ARM64. In alternativa, su Linux con Android SDK/NDK e Buildozer configurati eseguire buildozer android debug. Questa consegna contiene i sorgenti. La compilazione, il login, la 2FA e l’esecuzione su telefono reale richiedono collaudo. Nessuna pubblicazione effettuata.

## Verifiche riproducibili

Eseguire python -m unittest discover -s tests dalla radice. Non richiede dipendenze esterne. I test usano un client simulato. La schermata richiede Kivy e il collegamento reale richiede instagrapi. La sessione viene mantenuta nella memoria del processo. Le password non vengono scritte dall’app in un database o file. La dipendenza non ufficiale fa parte del perimetro da verificare prima del rilascio. La protezione nominativa inserita vale per la scansione corrente. Controllo e azione sono richieste distinte: il rapporto può cambiare tra le due.

## Struttura

main.py gestisce interfaccia italiana, login, lavoro in background rispetto alla UI e arresto quando l’app passa in secondo piano. engine.py identifica per ID i seguiti non reciproci, controlla la cardinalità prima e dopo la lettura e verifica il rapporto attuale. La mancata conferma interrompe l’elaborazione. Il passaggio in secondo piano non avvia una pianificazione periodica.

## Pause per profilo

La versione 0.3 conserva le restrizioni riconosciute per nome utente nel database privato del dispositivo. Con HTTP 429 o un errore di limitazione riconosciuto, usa Retry-After se disponibile (secondi o data HTTP). Senza un valore valido mostra una pausa di durata sconosciuta. Alla scadenza aggiorna localmente il messaggio. Il pulsante di verifica consente di dichiarare che la funzione è tornata disponibile in Instagram e avviare una nuova analisi. L'app non legge gli avvisi visualizzati esclusivamente nell'app ufficiale. La scadenza tecnica della richiesta può differire dalla durata della restrizione sul profilo.
