YoutubeDownloader

O YoutubeDownloader é uma aplicação desktop desenvolvida em Python voltada para a transferência de vídeos do YouTube através de uma interface gráfica simples e responsiva.

-----------------------------------------------------------------------------------

## Sobre o Projeto

A aplicação permite que o usuário informe o link do vídeo do YouTube e selecione o diretório de destino no sistema de arquivos local para salvar o conteúdo. 

Para evitar o congelamento da interface durante operações de rede e processamento assíncrono, a aplicação utiliza arquitetura baseada em threads e filas de comunicação.

### Principais Características
* Seleção de diretório de destino através do gerenciador de arquivos nativo.
* Processamento de download em segundo plano com multithreading.
* Atualização de status e controle de eventos assíncronos.

-----------------------------------------------------------------------------------

## Tecnologias e Bibliotecas

* Linguagem Base: Python 3
* Interface Gráfica: customtkinter, tkinter (filedialog, Canvas)
* Gerenciamento de Processos e Concorrência: threading, queue
* Integração com Sistema Operacional: os, sys, time

-----------------------------------------------------------------------------------

## Autora

Desenvolvido por Meive Archangelo Fratelli.
* GitHub: https://github.com/MeiveFratelli
* LinkedIn: https://www.linkedin.com/in/meive-fratelli/
