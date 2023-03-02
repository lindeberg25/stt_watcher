import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
from multiprocessing import Pool, cpu_count
from stomp import Connection, ConnectionListener, PrintingListener
import whisper
import torch
import time
import logging
import librosa


# O código é responsável por monitorar um diretório específico em busca de novos arquivos criados e, em seguida, 
# processar cada arquivo encontrado em uma thread separada usando uma piscina de processos. Após o processamento do arquivo, 
# o código envia uma mensagem para um servidor de mensagens ActiveMQ usando o protocolo STOMP


# Classe para tratar eventos de conexão do ActiveMQ
class MyListener(ConnectionListener):
    def on_error(self, headers, message):
        print('received an error "%s"' % message)

    def on_message(self, headers, message):
        print('received a message "%s"' % message)

# Classe para tratar eventos de criação de arquivos
class MyHandler(FileSystemEventHandler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def on_created(self, event):
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Novo arquivo criado
            #print(f"Arquivo de áudio criado: {event.src_path}")
            logging.info(f"Arquivo de áudio criado: {event.src_path}")
            self.queue.put(event.src_path)

# Função que processa o arquivo e envia uma mensagem para o ActiveMQ
def process_file(model, file_path, amq_host, amq_port, amq_user, amq_password, amq_queue):
    
    
    # Processar o arquivo aqui...
    #time.sleep(5) # Simulando o processamento do arquivo
    #model = whisper.load_model("medium.pt", device=DEVICE)
    
    start = time.time()
    logging.info("Inicia transcrição")
    duration = librosa.get_duration(path=file_path)
    result = model.transcribe(file_path, language="pt")
    logging.info("Finaliza transcrição")
    logging.info( result['text'])
    logging.info("Duração do áudio %s seconds " % duration)
    logging.info("Tempo de transcrição %s seconds " % (time.time() - start))
    #logging.info(result)
    



    # Enviar a mensagem para a fila do AMQ
    #conn = Connection(host_and_ports=[(amq_host, amq_port)])
    #conn.set_listener('', MyListener())
    #conn.start()
    #conn.connect(amq_user, amq_password)
    #conn.send(amq_queue, f"Arquivo processado: {file_path}")
    #conn.disconnect()

# Função para envolver a função de processamento de arquivos com argumentos
def process_file_wrapper(args):
    return process_file(*args)

# Classe que observa o diretório especificado e processa novos arquivos em uma thread separada
class Watcher:
    def __init__(self, model, path, amq_host, amq_port, amq_user, amq_password, amq_queue):
        self.model = model
        self.path = path
        self.queue = Queue()
        self.amq_host = amq_host
        self.amq_port = amq_port
        self.amq_user = amq_user
        self.amq_password = amq_password
        self.amq_queue = amq_queue
    
    def run(self):
        event_handler = MyHandler(self.queue)
        observer = Observer()
        observer.schedule(event_handler, path=self.path, recursive=True)
        observer.start()

        # Cria um pool de processos para executar a função process_file para cada novo arquivo encontrado
        with Pool(processes=min(cpu_count() - 1, 10)) as pool:
            while True:
                if not self.queue.empty():
                    file_path = self.queue.get()
                    logging.info("Pegou áudio da fila")
                
                    pool.apply(process_file_wrapper, [(file_path, self.model, self.amq_host, self.amq_port, self.amq_user, self.amq_password, self.amq_queue)])
                time.sleep(1)

        observer.stop()
        observer.join()

if __name__ == "__main__":
    
    # Check if NVIDIA GPU is available
    torch.cuda.is_available()
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    
    model = whisper.load_model("medium.pt", device=DEVICE)
    logging.basicConfig(filename='stt_watcher.log', level=logging.INFO)
    watcher = Watcher(model, "./audio", "localhost", 61613, "user", "password", "/queue/myqueue")
    logging.info('Monitora pasta de áudios do SIS')
    watcher.run()
    logging.info('Finaliza monitoração de pasta de áudio do SIS')
