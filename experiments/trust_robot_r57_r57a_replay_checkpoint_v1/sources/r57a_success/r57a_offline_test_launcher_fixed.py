import builtins,io,os,pathlib,runpy,socket,sys
target=pathlib.Path(sys.argv[1]).resolve()
def gate(p):
 try: s=os.fsdecode(os.fspath(p)).lower()
 except TypeError: return
 if "/recorded_m2dgr_train/" in s or "/confirmation_test/" in s: raise RuntimeError("R57_REPLAY_FORBIDDEN_SOURCE")
o=builtins.open; i=io.open; oo=os.open
def safe_open(p,*a,**kw): gate(p); return o(p,*a,**kw)
def safe_io(p,*a,**kw): gate(p); return i(p,*a,**kw)
def safe_os(p,*a,**kw): gate(p); return oo(p,*a,**kw)
builtins.open=safe_open;io.open=safe_io;os.open=safe_os
class DeniedSocket(socket.socket):
 def connect(self,*a,**kw): raise RuntimeError("R57_REPLAY_NETWORK_DENIED")
 def connect_ex(self,*a,**kw): raise RuntimeError("R57_REPLAY_NETWORK_DENIED")
 def sendto(self,*a,**kw): raise RuntimeError("R57_REPLAY_NETWORK_DENIED")
socket.socket=DeniedSocket
def no_network(*a,**kw): raise RuntimeError("R57_REPLAY_NETWORK_DENIED")
socket.create_connection=no_network;socket.getaddrinfo=no_network
sys.path.insert(0,str(target.parent));sys.argv=[str(target),str(target.parent),str(pathlib.Path(sys.argv[2]).resolve()),str(target.parent.parent)]
runpy.run_path(str(target),run_name="__main__")
