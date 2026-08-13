#!/usr/bin/env python3
"""Lockheed Martin Linux Terminal Lab — progressive, sandboxed terminal training."""
from __future__ import annotations

import difflib, fnmatch, glob, os, re, shlex, shutil, stat, string, subprocess, tempfile, textwrap, time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import tkinter as tk
from tkinter import ttk

APP_TITLE = "Lockheed Martin • Linux Terminal Lab — V4"
BUILD_ID = "V4"
HOST = "linuxtraining22"
USER = "trainee"
HOME = "/home/trainee"
CONTAINER_IMAGES = ("lockheed-linux-trainer:latest", "ubuntu:24.04", "debian:bookworm-slim")

BG="#08111F"; SURFACE="#0F1B2D"; SURFACE2="#13243B"; SURFACE3="#0C1626"; BORDER="#203754"
TEXT="#E6EEF8"; SOFT="#A9BCD4"; MUTED="#7E94AF"; ACCENT="#41C7FF"; ACCENT2="#69F0D0"
SUCCESS="#38D981"; ERROR="#FF8B8B"; TERM_BG="#050B14"; TERM_FG="#D9E7F5"; BTN="#17304F"; BTN_ACTIVE="#214269"

@dataclass
class Result:
    name: str
    args: List[str]
    raw: str
    output: str = ""
    success: bool = True
    meta: Dict[str, object] = field(default_factory=dict)

@dataclass
class Lesson:
    module: str
    title: str
    why: str
    task: str
    examples: Tuple[str, ...]
    hint: str
    check: Callable[["LinuxTrainerApp", Optional[Result]], bool]
    done: bool = False

class VirtualFS:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="linux_terminal_lab_"))
        self.cwd = HOME
        self.prev = HOME
        self.build()

    def cleanup(self): shutil.rmtree(self.root, ignore_errors=True)

    @staticmethod
    def norm(p: str) -> str:
        parts=[]
        for x in p.split('/'):
            if x in ('','.'): continue
            if x=='..':
                if parts: parts.pop()
            else: parts.append(x)
        return '/' + '/'.join(parts)

    def resolve(self, p: str, env: Optional[Dict[str,str]]=None) -> str:
        env=env or {}; p=p or '.'
        if p=='~': p=env.get('HOME',HOME)
        elif p.startswith('~/'): p=env.get('HOME',HOME).rstrip('/') + p[1:]
        return self.norm(p if p.startswith('/') else self.cwd.rstrip('/')+'/'+p)

    def real(self, p: str, env: Optional[Dict[str,str]]=None) -> Path:
        vp=self.resolve(p,env); target=(self.root/vp.lstrip('/')).resolve(); rr=self.root.resolve()
        if os.path.commonpath([str(rr),str(target)]) != str(rr): raise ValueError("path escapes sandbox")
        return target

    def virtual(self, p: Path) -> str:
        return '/' + str(p.resolve().relative_to(self.root.resolve())).replace(os.sep,'/')

    def exists(self,p):
        try: return self.real(p).exists()
        except Exception: return False
    def is_file(self,p):
        try: return self.real(p).is_file()
        except Exception: return False
    def is_dir(self,p):
        try: return self.real(p).is_dir()
        except Exception: return False
    def read(self,p): return self.real(p).read_text(encoding='utf-8',errors='replace')
    def write(self,p,s):
        q=self.real(p); q.parent.mkdir(parents=True,exist_ok=True); q.write_text(s,encoding='utf-8')

    def cd(self, target: str, env: Dict[str,str]):
        vp=self.prev if target=='-' else self.resolve(target or env.get('HOME',HOME),env); q=self.real(vp,env)
        if not q.exists(): return False,f"bash: cd: {target}: No such file or directory\n"
        if not q.is_dir(): return False,f"bash: cd: {target}: Not a directory\n"
        old=self.cwd; self.prev=old; self.cwd=vp
        return True,(self.cwd+'\n' if target=='-' else '')

    def expand_glob(self, token: str, env: Dict[str,str]) -> List[str]:
        if not any(c in token for c in '*?['): return [token]
        patt=str(self.root/self.resolve(token,env).lstrip('/')); hits=glob.glob(patt)
        return [self.virtual(Path(x)) for x in hits] or [token]

    def build(self):
        dirs=[
            '/home/trainee/Documents/onboarding','/home/trainee/Downloads','/home/trainee/projects/atlas/src',
            '/home/trainee/projects/atlas/config','/home/trainee/scripts','/home/trainee/archive','/home/trainee/.config',
            '/opt/training/data','/opt/training/examples','/etc/training','/var/log/training','/srv/releases/atlas-1.4.2','/tmp']
        for d in dirs: self.real(d).mkdir(parents=True,exist_ok=True)
        files={
            '/home/trainee/Documents/onboarding/handbook.txt':'''Linux New-Hire Onboarding Handbook\n=================================\nUse the terminal to inspect, copy, search, edit, and validate files.\n''',
            '/home/trainee/projects/atlas/README.md':'''# Atlas Training Service\nOwner: Platform Engineering\nEnvironment: training\nRelease: 1.4.2\n''',
            '/home/trainee/projects/atlas/config/dev.conf':'''service_name=atlas\nenvironment=development\nenabled=false\nowner=unset\nlog_level=INFO\nport=8080\n''',
            '/home/trainee/projects/atlas/src/app.py':'''def healthcheck():\n    return {"status": "ok", "service": "atlas"}\n''',
            '/home/trainee/scripts/report.sh':'''#!/usr/bin/env bash\necho "Atlas training report"\ngrep ERROR /var/log/training/app.log\n''',
            '/home/trainee/notes.txt':'Linux training notes\n',
            '/home/trainee/.bashrc':"export EDITOR=vim\nalias ll='ls -alF'\n",
            '/home/trainee/.config/trainer.conf':'theme=dark\nhints=enabled\n',
            '/opt/training/data/systems.csv':'''hostname,environment,status\natlas-dev-01,dev,online\natlas-dev-02,dev,online\natlas-qa-01,qa,degraded\natlas-prod-01,prod,online\natlas-prod-02,prod,online\n''',
            '/opt/training/data/owners.csv':'''service,owner\natlas,platform\ntelemetry,systems\ngateway,network\narchive,operations\n''',
            '/opt/training/examples/service.conf':'''service_name=atlas\nenabled=true\nowner=platform\nlog_level=INFO\nport=8080\n''',
            '/etc/training/service.conf':'''service_name=atlas\nenabled=false\nowner=unset\nlog_level=INFO\nport=8080\n''',
            '/etc/training/hosts.allow':'atlas-dev-01\natlas-dev-02\natlas-qa-01\n',
            '/var/log/training/app.log':'''2026-08-12 08:00:01 INFO  atlas service starting\n2026-08-12 08:00:03 INFO  loaded configuration\n2026-08-12 08:02:14 WARN  response time 842ms route=/health\n2026-08-12 08:03:09 ERROR database connection retry=1\n2026-08-12 08:03:12 ERROR database connection retry=2\n2026-08-12 08:03:18 INFO  database connection restored\n2026-08-12 08:05:40 WARN  disk usage=78%\n2026-08-12 08:07:55 ERROR checksum mismatch file=atlas.pkg\n2026-08-12 08:09:10 INFO  health check passed\n''',
            '/var/log/training/auth.log':'''2026-08-12 07:54:10 INFO login user=trainee source=console\n2026-08-12 08:01:44 WARN login-failure user=svc_atlas source=10.10.4.21\n2026-08-12 08:04:31 INFO login user=svc_atlas source=10.10.4.21\n''',
            '/srv/releases/atlas-1.4.2/manifest.txt':'release=atlas-1.4.2\nchecksum=7f3e2c91\napproved=true\n',
            '/home/trainee/archive/old_notes.tmp':'obsolete scratch notes\n'}
        for p,s in files.items(): self.write(p,s)
        now=time.time()
        for i,p in enumerate(['/home/trainee/notes.txt','/home/trainee/projects/atlas/README.md','/home/trainee/scripts/report.sh','/home/trainee/.bashrc']):
            os.utime(self.real(p),(now-(4-i)*3600,now-(4-i)*3600))
        try: os.chmod(self.real('/home/trainee/scripts/report.sh'),0o644)
        except OSError: pass

class ContainerBackend:
    def __init__(self,fs:VirtualFS): self.fs=fs; self.runtime=None; self.image=None; self.detect()
    @property
    def available(self): return bool(self.runtime and self.image)
    @property
    def label(self): return 'REAL LINUX' if self.available else 'PORTABLE'
    def detect(self):
        for rt in ('docker','podman'):
            exe=shutil.which(rt)
            if not exe: continue
            for image in CONTAINER_IMAGES:
                try: ok=subprocess.run([exe,'image','inspect',image],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2).returncode==0
                except Exception: ok=False
                if ok: self.runtime,self.image=exe,image; return
    def run(self,cmd,cwd,env,stdin=''):
        if not self.available: return Result(cmd.split()[0],[],cmd,f"{cmd.split()[0]}: command not found\n",False)
        a=[self.runtime,'run','--rm','-i','--network','none','--memory','256m','--cpus','1','--pids-limit','128','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only',
           '-v',f"{self.fs.root/'home'}:/home:rw",'-v',f"{self.fs.root/'opt'}:/opt:rw",'-v',f"{self.fs.root/'srv'}:/srv:rw",'-v',f"{self.fs.root/'tmp'}:/tmp:rw",'-v',f"{self.fs.root/'var'/'log'/'training'}:/var/log/training:rw",'-v',f"{self.fs.root/'etc'/'training'}:/etc/training:rw",'-w',cwd]
        if hasattr(os,'getuid') and hasattr(os,'getgid'):
            a += ['--user',f'{os.getuid()}:{os.getgid()}']
        for k in ('HOME','USER','LOGNAME','EDITOR','LAB_ENV'):
            if k in env: a+=['-e',f'{k}={env[k]}']
        a += [self.image,'bash','-lc',cmd]
        try: p=subprocess.run(a,input=stdin,text=True,capture_output=True,timeout=8)
        except subprocess.TimeoutExpired: return Result('external',[],cmd,'command timed out after 8 seconds\n',False)
        except OSError as e: return Result('external',[],cmd,f'container backend error: {e}\n',False)
        try: parts=shlex.split(cmd); name=parts[0]; args=parts[1:]
        except Exception: name,args='external',[]
        return Result(name,args,cmd,(p.stdout or '')+(p.stderr or ''),p.returncode==0,{'backend':'container'})

class Shell:
    def __init__(self,fs:VirtualFS,open_editor:Callable[[str,str],None],clear_screen:Callable[[],None]):
        self.fs=fs; self.open_editor=open_editor; self.clear_screen=clear_screen
        self.env={'HOME':HOME,'USER':USER,'LOGNAME':USER,'HOSTNAME':HOST,'SHELL':'/bin/bash','EDITOR':'vim','LAB_ENV':'training','PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}
        self.aliases={'ll':'ls -alF','la':'ls -A','l':'ls -CF'}; self.history=[]; self.last_status=0; self.backend=ContainerBackend(fs)

    def commands(self):
        return sorted({'pwd','ls','ll','la','l','cd','mkdir','rmdir','touch','cp','mv','rm','cat','less','more','head','tail','grep','wc','sort','uniq','cut','tr','find','chmod','stat','file','basename','dirname','diff','tree','du','df','echo','printf','tee','sed','awk','whoami','id','hostname','uname','date','env','export','unset','history','alias','unalias','which','type','ps','clear','man','help','commands','vi','vim','gvim','nano','true','false'})

    @staticmethod
    def split_unquoted(text:str,ops:Sequence[str]):
        out=[]; buf=[]; quote=None; esc=False; i=0; ops=sorted(ops,key=len,reverse=True)
        while i<len(text):
            c=text[i]
            if esc: buf.append(c); esc=False; i+=1; continue
            if c=='\\' and quote!="'": buf.append(c); esc=True; i+=1; continue
            if c in "'\"":
                if quote is None: quote=c
                elif quote==c: quote=None
                buf.append(c); i+=1; continue
            if quote is None:
                hit=next((op for op in ops if text.startswith(op,i)),None)
                if hit: out.append((''.join(buf).strip(),hit)); buf=[]; i+=len(hit); continue
            buf.append(c); i+=1
        out.append((''.join(buf).strip(),None)); return out

    def expand_vars(self,text):
        """Expand shell variables outside single quotes.

        This intentionally covers the common interactive forms used by the lab
        (`$NAME`, `${NAME}`, and `$?`) while preserving single-quoted literals,
        matching normal shell expectations much more closely than a global regex.
        """
        out=[]; i=0; quote=None
        while i<len(text):
            c=text[i]
            if c=="'":
                quote=None if quote=="'" else ("'" if quote is None else quote); out.append(c); i+=1; continue
            if c=='"':
                quote=None if quote=='"' else ('"' if quote is None else quote); out.append(c); i+=1; continue
            if c=='\\' and quote!="'" and i+1<len(text):
                out.append(c); out.append(text[i+1]); i+=2; continue
            if c=='$' and quote!="'":
                if i+1<len(text) and text[i+1]=='?':
                    out.append(str(self.last_status)); i+=2; continue
                if i+1<len(text) and text[i+1]=='{':
                    end=text.find('}',i+2)
                    if end!=-1:
                        name=text[i+2:end]
                        if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):
                            out.append(self.env.get(name,'')); i=end+1; continue
                m=re.match(r'\$([A-Za-z_][A-Za-z0-9_]*)',text[i:])
                if m:
                    out.append(self.env.get(m.group(1),'')); i+=len(m.group(0)); continue
            out.append(c); i+=1
        return ''.join(out)

    def run(self,line:str):
        if not line: return Result('',[],line,'',True)
        self.history.append(line); seq=self.split_unquoted(line,['&&','||',';'])
        last=Result('',[],line,'',True); combined=[]; prev=None
        for part,op_after in seq:
            if not part: prev=op_after; continue
            execute=not(prev=='&&' and not last.success) and not(prev=='||' and last.success)
            if execute: last=self.pipeline(self.expand_vars(part)); combined.append(last.output)
            prev=op_after
        last.raw=line; last.output=''.join(combined); self.last_status=0 if last.success else 1; return last

    def pipeline(self,text):
        stages=self.split_unquoted(text,['|']); stdin=''; last=Result('',[],text,'',True)
        for stage,_ in stages:
            if stage: last=self.stage(stage,stdin); stdin=last.output
        return last

    def stage(self,text,stdin=''):
        try:
            lex=shlex.shlex(text,posix=True,punctuation_chars='<>'); lex.whitespace_split=True; lex.commenters=''; tok=list(lex)
        except ValueError as e: return Result('parse_error',[],text,f'bash: {e}\n',False)
        if not tok: return Result('',[],text,'',True)
        inp=None; outp=None; append=False; clean=[]; i=0
        while i<len(tok):
            if tok[i] in ('<','>','>>'):
                if i+1>=len(tok): return Result('parse_error',[],text,f"bash: syntax error near unexpected token '{tok[i]}'\n",False)
                if tok[i]=='<': inp=tok[i+1]
                else: outp=tok[i+1]; append=tok[i]=='>>'
                i+=2
            else: clean.append(tok[i]); i+=1
        if inp:
            try: stdin=self.fs.read(inp)
            except OSError: return Result(clean[0] if clean else '',clean[1:],text,f'bash: {inp}: No such file or directory\n',False)
        if not clean: return Result('',[],text,'',True)
        if len(clean)==1 and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=.*$',clean[0]):
            k,v=clean[0].split('=',1); self.env[k]=v; res=Result('assignment',[clean[0]],text,'',True)
        else:
            if clean[0] in self.aliases: clean=shlex.split(self.aliases[clean[0]])+clean[1:]
            res=self.dispatch(clean[0],clean[1:],text,stdin)
        if outp and res.success:
            q=self.fs.real(outp,self.env)
            if not q.parent.exists(): return Result(res.name,res.args,text,f'bash: {outp}: No such file or directory\n',False)
            with q.open('a' if append else 'w',encoding='utf-8') as f: f.write(res.output)
            res.meta['redirected_to']=self.fs.resolve(outp,self.env); res.output=''
        return res

    def dispatch(self,name,args,raw,stdin):
        f=getattr(self,'cmd_'+name,None)
        if f:
            # Stateful shell built-ins must stay local so cwd/environment/history
            # remain persistent. Everything else may fall through to the optional
            # Linux container when the portable implementation reaches its limit.
            stateful={'cd','export','unset','alias','unalias','history','clear','vi','vim','gvim','nano'}
            try:
                res=f(args,raw,name,stdin)
            except Exception as exc:
                if self.backend.available and name not in stateful:
                    return self.backend.run(shlex.join([name]+args),self.fs.cwd,self.env,stdin)
                return Result(name,args,raw,f'{name}: invalid or unsupported arguments ({exc})\n',False,{'guarded_exception':type(exc).__name__})
            unsupported=('invalid option','unsupported predicate','portable mode supports','unsupported in portable mode')
            if self.backend.available and name not in stateful and not res.success and any(x in res.output.lower() for x in unsupported):
                return self.backend.run(shlex.join([name]+args),self.fs.cwd,self.env,stdin)
            return res
        if name in ('ll','la','l'):
            z=shlex.split(self.aliases[name])+args; return self.dispatch(z[0],z[1:],raw,stdin)
        if self.backend.available: return self.backend.run(shlex.join([name]+args),self.fs.cwd,self.env,stdin)
        return Result(name,args,raw,f'{name}: command not found\n',False)

    @staticmethod
    def flags(args,allowed):
        fs=set(); operands=[]; end=False
        for a in args:
            if end: operands.append(a)
            elif a=='--': end=True
            elif a.startswith('--'): return fs,operands,a
            elif a.startswith('-') and a!='-':
                for c in a[1:]:
                    if c not in allowed: return fs,operands,'-'+c
                    fs.add(c)
            else: operands.append(a)
        return fs,operands,None

    def paths(self,ops:Iterable[str]):
        out=[]
        for x in ops: out.extend(self.fs.expand_glob(x,self.env))
        return out

    @staticmethod
    def human(n):
        x=float(n)
        for u in ('B','K','M','G','T'):
            if x<1024 or u=='T': return (f'{int(x)}B' if u=='B' else f'{x:.1f}{u}'.replace('.0',''))
            x/=1024

    def ls_item(self,p:Path,fs:set,display_name:Optional[str]=None):
        name=display_name if display_name is not None else (p.name or '/')
        if 'F' in fs:
            if p.is_dir(): name+='/'
            elif p.is_symlink(): name+='@'
            elif p.is_file() and os.access(p,os.X_OK): name+='*'
        if 'l' not in fs: return name
        st=p.lstat(); size=self.human(st.st_size) if 'h' in fs else str(st.st_size); mt=time.strftime('%b %d %H:%M',time.localtime(st.st_mtime))
        return f'{stat.filemode(st.st_mode)} 1 {USER:<8} training {size:>7} {mt} {name}'

    def read_sources(self,ops,stdin,cmd):
        if not ops: return [('',stdin)],[],True
        src=[]; err=[]; ok=True
        for t in self.paths(ops):
            q=self.fs.real(t,self.env)
            if not q.exists() or not q.is_file(): err.append(f'{cmd}: {t}: No such file or directory\n'); ok=False
            else: src.append((t,q.read_text(encoding='utf-8',errors='replace')))
        return src,err,ok

    def cmd_pwd(self,a,r,n,s):
        if any(x not in ('-L','-P','--logical','--physical') for x in a):
            return Result(n,a,r,'pwd: invalid option or too many arguments\n',False)
        return Result(n,a,r,self.fs.cwd+'\n',True,{'mode':'physical' if ('-P' in a or '--physical' in a) else 'logical'})
    def cmd_cd(self,a,r,n,s):
        if len(a)>1: return Result(n,a,r,'bash: cd: too many arguments\n',False)
        ok,o=self.fs.cd(a[0] if a else self.env['HOME'],self.env); return Result(n,a,r,o,ok,{'cwd':self.fs.cwd})
    def cmd_ls(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'alhtrRFS1Ad')
        if bad:return Result(n,a,r,f"ls: invalid option -- '{bad.lstrip('-')}'\n",False)
        ops=self.paths(ops or ['.']); out=[]; ok=True; show_hidden=('a'in fs or 'A'in fs)

        def sorted_entries(q):
            entries=list(q.iterdir())
            entries=[p for p in entries if show_hidden or not p.name.startswith('.')]
            if 't'in fs:entries.sort(key=lambda p:p.stat().st_mtime,reverse=True)
            elif 'S'in fs:entries.sort(key=lambda p:p.stat().st_size,reverse=True)
            else:entries.sort(key=lambda p:p.name.lower())
            if 'r'in fs:entries.reverse()
            return entries

        def render_dir(q,display,heading=False):
            if heading:out.append(f'{display}:\n')
            entries=sorted_entries(q)
            items=[]
            if 'a'in fs:
                parent_v=self.fs.norm(self.fs.virtual(q)+'/..')
                parent_q=self.fs.real(parent_v,self.env)
                items.extend([(q,'.'),(parent_q,'..')])
            items.extend((p,None) for p in entries)
            if 'l'in fs or '1'in fs:
                out.extend(self.ls_item(p,fs,label)+'\n' for p,label in items)
            else:
                out.append('  '.join(self.ls_item(p,fs,label) for p,label in items)+('\n' if items else ''))
            if 'R'in fs:
                children=[p for p in entries if p.is_dir() and not p.is_symlink()]
                for child in children:
                    out.append('\n')
                    child_display=(display.rstrip('/')+'/'+child.name) if display not in ('.','/') else (('./'+child.name) if display=='.' else '/'+child.name)
                    render_dir(child,child_display,True)

        for idx,t in enumerate(ops):
            q=self.fs.real(t,self.env)
            if not q.exists():out.append(f"ls: cannot access '{t}': No such file or directory\n");ok=False;continue
            if q.is_file() or 'd'in fs:
                if len(ops)>1:out.append(f'{t}:\n')
                out.append(self.ls_item(q,fs)+'\n')
            else:
                render_dir(q,t,heading=(len(ops)>1 or 'R'in fs))
            if idx!=len(ops)-1:out.append('\n')
        return Result(n,a,r,''.join(out),ok,{'flags':fs,'paths':ops})
    def cmd_mkdir(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'pv')
        if bad or not ops: return Result(n,a,r,'mkdir: missing operand\n' if not ops else f'mkdir: invalid option {bad}\n',False)
        out=[]; ok=True
        for t in self.paths(ops):
            try: self.fs.real(t,self.env).mkdir(parents='p' in fs,exist_ok='p' in fs); out.append(f"mkdir: created directory '{t}'\n" if 'v' in fs else '')
            except OSError as e: out.append(f"mkdir: cannot create directory '{t}': {e.strerror}\n"); ok=False
        return Result(n,a,r,''.join(out),ok)
    def cmd_rmdir(self,a,r,n,s):
        if not a:return Result(n,a,r,'rmdir: missing operand\n',False)
        out=[];ok=True
        for t in a:
            try:self.fs.real(t,self.env).rmdir()
            except OSError as e:out.append(f"rmdir: failed to remove '{t}': {e.strerror}\n");ok=False
        return Result(n,a,r,''.join(out),ok)
    def cmd_touch(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'c')
        if bad or not ops:return Result(n,a,r,'touch: missing file operand\n',False)
        out=[];ok=True
        for t in self.paths(ops):
            q=self.fs.real(t,self.env)
            if not q.parent.exists():out.append(f"touch: cannot touch '{t}': No such file or directory\n");ok=False
            elif not('c'in fs and not q.exists()):q.touch()
        return Result(n,a,r,''.join(out),ok)
    def cmd_cp(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'rRpvf'); ops=self.paths(ops)
        if bad:return Result(n,a,r,f'cp: invalid option {bad}\n',False)
        if len(ops)<2:return Result(n,a,r,'cp: missing destination file operand\n',False)
        srcs,destt=ops[:-1],ops[-1]; dest=self.fs.real(destt,self.env); out=[];ok=True
        if destt.endswith('/') and not dest.is_dir():return Result(n,a,r,f"cp: target '{destt}' is not a directory\n",False)
        if len(srcs)>1 and not dest.is_dir():return Result(n,a,r,f"cp: target '{destt}' is not a directory\n",False)
        for t in srcs:
            q=self.fs.real(t,self.env)
            if not q.exists():out.append(f"cp: cannot stat '{t}': No such file or directory\n");ok=False;continue
            target=dest/q.name if dest.exists() and dest.is_dir() else dest
            try:
                if q.is_dir():
                    if not({'r','R'}&fs):out.append(f"cp: -r not specified; omitting directory '{t}'\n");ok=False;continue
                    shutil.copytree(q,target,dirs_exist_ok=True)
                else:
                    if not target.parent.exists(): raise FileNotFoundError()
                    shutil.copy2(q,target) if 'p'in fs else shutil.copy(q,target)
                if 'v'in fs:out.append(f"'{t}' -> '{self.fs.virtual(target)}'\n")
            except OSError as e:out.append(f"cp: cannot copy '{t}': {getattr(e,'strerror',None) or e}\n");ok=False
        return Result(n,a,r,''.join(out),ok)
    def cmd_mv(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'vf');ops=self.paths(ops)
        if bad or len(ops)<2:return Result(n,a,r,'mv: missing destination file operand\n',False)
        srcs,destt=ops[:-1],ops[-1];dest=self.fs.real(destt,self.env);out=[];ok=True
        if destt.endswith('/') and not dest.is_dir():return Result(n,a,r,f"mv: target '{destt}' is not a directory\n",False)
        if len(srcs)>1 and not dest.is_dir():return Result(n,a,r,f"mv: target '{destt}' is not a directory\n",False)
        for t in srcs:
            q=self.fs.real(t,self.env)
            if not q.exists():out.append(f"mv: cannot stat '{t}'\n");ok=False;continue
            target=dest/q.name if dest.exists() and dest.is_dir() else dest
            try:shutil.move(str(q),str(target));out.append(f"renamed '{t}' -> '{self.fs.virtual(target)}'\n" if 'v'in fs else '')
            except OSError as e:out.append(f'mv: {e}\n');ok=False
        return Result(n,a,r,''.join(out),ok)
    def cmd_rm(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'rRfvi');ops=self.paths(ops)
        if bad or not ops:return Result(n,a,r,'rm: missing operand\n',False)
        out=[];ok=True
        for t in ops:
            q=self.fs.real(t,self.env)
            if not q.exists() and not q.is_symlink():
                if 'f'not in fs:out.append(f"rm: cannot remove '{t}': No such file or directory\n");ok=False
                continue
            if q.is_dir() and not q.is_symlink():
                if not({'r','R'}&fs):out.append(f"rm: cannot remove '{t}': Is a directory\n");ok=False;continue
                shutil.rmtree(q)
            else:q.unlink()
            if 'v'in fs:out.append(f"removed '{t}'\n")
        return Result(n,a,r,''.join(out),ok)
    def cmd_cat(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'nb')
        if bad:return Result(n,a,r,f'cat: invalid option {bad}\n',False)
        src,err,ok=self.read_sources(ops,s,'cat');out=err[:]
        for _,c in src:
            if 'n'in fs or 'b'in fs:
                k=1
                for line in c.splitlines(True):
                    number='n'in fs or ('b'in fs and line.strip());out.append(f'{k:6}\t{line}' if number else line);k+=1 if number else 0
            else:out.append(c+('' if not c or c.endswith('\n') else '\n'))
        return Result(n,a,r,''.join(out),ok)
    def cmd_less(self,a,r,n,s):return self.cmd_cat(a,r,n,s)
    def cmd_more(self,a,r,n,s):return self.cmd_cat(a,r,n,s)
    def countarg(self,a,default=10):
        count=default;ops=[];i=0
        while i<len(a):
            if a[i]=='-n' and i+1<len(a):
                try:count=int(a[i+1])
                except:return count,ops,'invalid number'
                i+=2
            elif re.fullmatch(r'-\d+',a[i]):count=int(a[i][1:]);i+=1
            else:ops.append(a[i]);i+=1
        return count,ops,None
    def cmd_head(self,a,r,n,s):
        c,ops,e=self.countarg(a)
        if e:return Result(n,a,r,'head: invalid number\n',False)
        src,err,ok=self.read_sources(ops,s,'head');return Result(n,a,r,''.join(err+[''.join(x.splitlines(True)[:c]) for _,x in src]),ok)
    def cmd_tail(self,a,r,n,s):
        if '-f'in a:return Result(n,a,r,'tail: live -f mode is disabled in this trainer\n',False)
        c,ops,e=self.countarg(a)
        if e:return Result(n,a,r,'tail: invalid number\n',False)
        src,err,ok=self.read_sources(ops,s,'tail');return Result(n,a,r,''.join(err+[''.join(x.splitlines(True)[-c:]) for _,x in src]),ok)
    def cmd_grep(self,a,r,n,s):
        ic=ln=inv=rec=count=files_only=ext=word=False;clean=[];i=0
        while i<len(a):
            x=a[i]
            if x=='--':clean+=a[i+1:];break
            if x.startswith('-') and x!='-':
                mapping={'i':'ic','n':'ln','v':'inv','r':'rec','R':'rec','c':'count','l':'files_only','E':'ext','w':'word'}
                if x=='--ignore-case':ic=True
                elif x=='--line-number':ln=True
                elif x=='--recursive':rec=True
                else:
                    for c in x[1:]:
                        if c not in mapping:return Result(n,a,r,f"grep: invalid option -- '{c}'\n",False)
                        if c=='i':ic=True
                        elif c=='n':ln=True
                        elif c=='v':inv=True
                        elif c in 'rR':rec=True
                        elif c=='c':count=True
                        elif c=='l':files_only=True
                        elif c=='E':ext=True
                        elif c=='w':word=True
                i+=1
            else:clean.append(x);i+=1
        if not clean:return Result(n,a,r,'grep: missing search pattern\n',False)
        patt=clean[0];fps=clean[1:];rp=patt if ext else re.escape(patt);rp=(r'\b(?:'+rp+r')\b') if word else rp
        try:rg=re.compile(rp,re.I if ic else 0)
        except re.error as e:return Result(n,a,r,f'grep: {e}\n',False)
        src=[];err=[];ok=True
        if fps:
            for t in self.paths(fps):
                q=self.fs.real(t,self.env)
                if q.is_dir() and rec:
                    for f in sorted(x for x in q.rglob('*') if x.is_file()):src.append((self.fs.virtual(f),f.read_text(encoding='utf-8',errors='replace')))
                elif q.is_file():src.append((t,q.read_text(encoding='utf-8',errors='replace')))
                else:err.append(f'grep: {t}: No such file or directory\n');ok=False
        else:src=[('',s)]
        out=err[:];total=0;multi=len(src)>1
        for label,content in src:
            hits=[]
            for num,line in enumerate(content.splitlines(),1):
                m=bool(rg.search(line));m=not m if inv else m
                if m:hits.append((num,line))
            total+=len(hits)
            if files_only and hits:out.append(label+'\n')
            elif count:out.append((f'{label}:' if multi and label else '')+str(len(hits))+'\n')
            else:
                for num,line in hits:out.append((f'{label}:' if multi and label else '')+(f'{num}:' if ln else '')+line+'\n')
        return Result(n,a,r,''.join(out),ok and total>0,{'matches':total,'line_numbers':ln,'ignore_case':ic,'recursive':rec})
    def cmd_wc(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'lwc')
        if bad:return Result(n,a,r,f'wc: invalid option {bad}\n',False)
        if not fs:fs=set('lwc')
        src,err,ok=self.read_sources(ops,s,'wc');out=err[:]
        for label,c in src:
            vals=[]
            if 'l'in fs:vals.append(str(len(c.splitlines())))
            if 'w'in fs:vals.append(str(len(c.split())))
            if 'c'in fs:vals.append(str(len(c.encode())))
            out.append(' '.join(f'{v:>7}' for v in vals)+(f' {label}' if label else '')+'\n')
        return Result(n,a,r,''.join(out),ok)
    def cmd_sort(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'rnu')
        if bad:return Result(n,a,r,f'sort: invalid option {bad}\n',False)
        src,err,ok=self.read_sources(ops,s,'sort');lines=[]
        for _,c in src:lines+=c.splitlines()
        if 'n'in fs:
            def key(v):
                try:return float(v.strip().split()[0])
                except:return 0.0
        else:key=lambda v:v
        lines.sort(key=key,reverse='r'in fs)
        if 'u'in fs:lines=list(dict.fromkeys(lines))
        return Result(n,a,r,''.join(err)+('\n'.join(lines)+('\n' if lines else '')),ok)
    def cmd_uniq(self,a,r,n,s):
        fs,ops,bad=self.flags(a,'cdu')
        if bad:return Result(n,a,r,f'uniq: invalid option {bad}\n',False)
        src,err,ok=self.read_sources(ops,s,'uniq');lines=[]
        for _,c in src:lines+=c.splitlines()
        groups=[]
        for line in lines:
            if groups and groups[-1][0]==line:groups[-1]=(line,groups[-1][1]+1)
            else:groups.append((line,1))
        out=err[:]
        for line,c in groups:
            if 'd'in fs and c<2:continue
            if 'u'in fs and c!=1:continue
            out.append((f'{c:7} ' if 'c'in fs else '')+line+'\n')
        return Result(n,a,r,''.join(out),ok)
    @staticmethod
    def numlist(spec):
        out=[]
        for p in spec.split(','):
            if '-'in p:
                x,y=p.split('-',1)
                if x.isdigit() and y.isdigit():out+=list(range(int(x),int(y)+1))
            elif p.isdigit():out.append(int(p))
        return out
    def cmd_cut(self,a,r,n,s):
        d='\t';fields=None;chars=None;ops=[];i=0
        while i<len(a):
            x=a[i]
            if x=='-d' and i+1<len(a):d=a[i+1];i+=2
            elif x.startswith('-d') and len(x)>2:d=x[2:];i+=1
            elif x=='-f' and i+1<len(a):fields=self.numlist(a[i+1]);i+=2
            elif x.startswith('-f') and len(x)>2:fields=self.numlist(x[2:]);i+=1
            elif x=='-c' and i+1<len(a):chars=self.numlist(a[i+1]);i+=2
            elif x.startswith('-c') and len(x)>2:chars=self.numlist(x[2:]);i+=1
            else:ops.append(x);i+=1
        if fields is None and chars is None:return Result(n,a,r,'cut: specify fields or characters\n',False)
        src,err,ok=self.read_sources(ops,s,'cut');out=err[:]
        for _,c in src:
            for line in c.splitlines():
                if fields is not None:
                    p=line.split(d);out.append(d.join(p[x-1] for x in fields if 1<=x<=len(p))+'\n')
                else:out.append(''.join(line[x-1] for x in (chars or []) if 1<=x<=len(line))+'\n')
        return Result(n,a,r,''.join(out),ok)
    @staticmethod
    def expand_tr_set(spec):
        classes={'[:lower:]':string.ascii_lowercase,'[:upper:]':string.ascii_uppercase,'[:digit:]':string.digits}
        for key,value in classes.items():spec=spec.replace(key,value)
        out=[];i=0
        while i<len(spec):
            if i+2<len(spec) and spec[i+1]=='-' and ord(spec[i])<=ord(spec[i+2]):
                out.extend(chr(c) for c in range(ord(spec[i]),ord(spec[i+2])+1));i+=3
            else:out.append(spec[i]);i+=1
        return ''.join(out)
    def cmd_tr(self,a,r,n,s):
        delete='-d'in a;clean=[x for x in a if x!='-d']
        if delete:
            if len(clean)!=1:return Result(n,a,r,'tr: missing operand\n',False)
            src=self.expand_tr_set(clean[0]);return Result(n,a,r,s.translate({ord(c):None for c in src}),True)
        if len(clean)!=2:return Result(n,a,r,'tr: missing operand\n',False)
        src,dst=map(self.expand_tr_set,clean)
        if not src:return Result(n,a,r,s,True)
        if not dst:return Result(n,a,r,'tr: empty replacement set\n',False)
        if len(dst)<len(src):dst=dst+dst[-1]*(len(src)-len(dst))
        else:dst=dst[:len(src)]
        return Result(n,a,r,s.translate(str.maketrans(src,dst)),True)
    def cmd_find(self,a,r,n,s):
        start='.';patt=None;typ=None;maxd=None;mind=0;i=0
        if a and not a[0].startswith('-'):start=a[0];i=1
        while i<len(a):
            x=a[i]
            if x=='-name' and i+1<len(a):patt=a[i+1];i+=2
            elif x=='-type' and i+1<len(a):typ=a[i+1];i+=2
            elif x=='-maxdepth' and i+1<len(a):
                try:maxd=int(a[i+1])
                except ValueError:return Result(n,a,r,f"find: invalid argument '{a[i+1]}' to -maxdepth\n",False)
                i+=2
            elif x=='-mindepth' and i+1<len(a):
                try:mind=int(a[i+1])
                except ValueError:return Result(n,a,r,f"find: invalid argument '{a[i+1]}' to -mindepth\n",False)
                i+=2
            else:return Result(n,a,r,f"find: unsupported predicate '{x}' in portable mode\n",False)
        root=self.fs.real(start,self.env)
        if not root.exists():return Result(n,a,r,f"find: '{start}': No such file or directory\n",False)
        out=[]
        for p in [root]+list(root.rglob('*')):
            depth=len(p.relative_to(root).parts)
            if depth<mind or (maxd is not None and depth>maxd):continue
            if patt and not fnmatch.fnmatch(p.name,patt):continue
            if typ=='f' and not p.is_file():continue
            if typ=='d' and not p.is_dir():continue
            if typ=='l' and not p.is_symlink():continue
            out.append(self.fs.virtual(p)+'\n')
        return Result(n,a,r,''.join(out),True,{'pattern':patt,'type':typ})
    @staticmethod
    def apply_mode(cur,mode,isdir=False):
        if re.fullmatch(r'[0-7]{3,4}',mode):return int(mode,8)
        out=cur
        for cl in mode.split(','):
            m=re.fullmatch(r'([ugoa]*)([+=-])([rwxX]+)',cl)
            if not m:raise ValueError(mode)
            who,op,per=m.groups();who=who or 'a';classes=set('ugo') if 'a'in who else set(who);bits=0
            for c in classes:
                sh={'u':6,'g':3,'o':0}[c];b=(4 if 'r'in per else 0)|(2 if 'w'in per else 0)|(1 if ('x'in per or ('X'in per and (isdir or cur&0o111))) else 0);bits|=b<<sh
            if op=='+':out|=bits
            elif op=='-':out&=~bits
            else:
                for c in classes:out&=~(0o7<<{'u':6,'g':3,'o':0}[c])
                out|=bits
        return out
    def cmd_chmod(self,a,r,n,s):
        rec='-R'in a;clean=[x for x in a if x!='-R']
        if len(clean)<2:return Result(n,a,r,'chmod: missing operand\n',False)
        mode=clean[0];out=[];ok=True
        for t in self.paths(clean[1:]):
            q=self.fs.real(t,self.env)
            if not q.exists():out.append(f"chmod: cannot access '{t}'\n");ok=False;continue
            items=[q]+(list(q.rglob('*')) if rec and q.is_dir() else [])
            try:
                for x in items:os.chmod(x,self.apply_mode(stat.S_IMODE(x.stat().st_mode),mode,x.is_dir()))
            except Exception as e:out.append(f'chmod: invalid mode {mode}: {e}\n');ok=False
        return Result(n,a,r,''.join(out),ok,{'mode':mode})
    def cmd_stat(self,a,r,n,s):
        if not a:return Result(n,a,r,'stat: missing operand\n',False)
        out=[];ok=True
        for t in self.paths(a):
            q=self.fs.real(t,self.env)
            if not q.exists():out.append(f"stat: cannot stat '{t}'\n");ok=False;continue
            st=q.stat();out.append(f"  File: {t}\n  Size: {st.st_size:<12} Type: {'directory' if q.is_dir() else 'regular file'}\nAccess: ({stat.S_IMODE(st.st_mode):04o}/{stat.filemode(st.st_mode)})  Uid: ({USER})   Gid: (training)\nModify: {datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ',timespec='seconds')}\n")
        return Result(n,a,r,''.join(out),ok)
    def cmd_file(self,a,r,n,s):
        if not a:return Result(n,a,r,'file: missing operand\n',False)
        out=[];ok=True
        for t in self.paths(a):
            q=self.fs.real(t,self.env)
            if not q.exists():out.append(f'{t}: cannot open\n');ok=False;continue
            kind='directory' if q.is_dir() else ('Bourne-Again shell script, ASCII text'+(' executable' if os.access(q,os.X_OK) else '') if q.suffix=='.sh' else 'CSV text' if q.suffix=='.csv' else 'Python script, ASCII text' if q.suffix=='.py' else 'ASCII text')
            out.append(f'{t}: {kind}\n')
        return Result(n,a,r,''.join(out),ok)
    def cmd_basename(self,a,r,n,s):return Result(n,a,r,(Path(a[0].rstrip('/')).name+'\n') if a else 'basename: missing operand\n',bool(a))
    def cmd_dirname(self,a,r,n,s):return Result(n,a,r,(str(Path(a[0]).parent).replace(os.sep,'/')+'\n') if a else 'dirname: missing operand\n',bool(a))
    def cmd_diff(self,a,r,n,s):
        unified='-u'in a or '--unified'in a;clean=[x for x in a if x not in ('-u','--unified')]
        if len(clean)!=2:return Result(n,a,r,'diff: missing operand\n',False)
        x,y=clean
        if not self.fs.is_file(x) or not self.fs.is_file(y):return Result(n,a,r,'diff: file not found\n',False)
        left=self.fs.read(x).splitlines(True);right=self.fs.read(y).splitlines(True)
        if left==right:return Result(n,a,r,'',True,{'different':False})
        o=''.join(difflib.unified_diff(left,right,fromfile=x,tofile=y)) if unified else ''.join(difflib.ndiff(left,right));return Result(n,a,r,o,False,{'different':True})
    def cmd_tree(self,a,r,n,s):
        show='-a'in a;dirs='-d'in a;clean=[x for x in a if x not in ('-a','-d')];root_t=clean[0] if clean else '.';root=self.fs.real(root_t,self.env)
        if not root.exists():return Result(n,a,r,f'{root_t} [error opening dir]\n',False)
        out=[root_t+'\n'];dc=fc=0
        def walk(p,prefix=''):
            nonlocal dc,fc
            e=[x for x in p.iterdir() if show or not x.name.startswith('.')];e=[x for x in e if not dirs or x.is_dir()];e.sort(key=lambda x:(not x.is_dir(),x.name.lower()))
            for i,x in enumerate(e):
                last=i==len(e)-1;out.append(prefix+('└── ' if last else '├── ')+x.name+('/' if x.is_dir() else '')+'\n')
                if x.is_dir():dc+=1;walk(x,prefix+('    ' if last else '│   '))
                else:fc+=1
        if root.is_dir():walk(root)
        out.append(f'\n{dc} directories, {fc} files\n');return Result(n,a,r,''.join(out),True)
    def cmd_du(self,a,r,n,s):
        human=any('h'in x[1:] for x in a if x.startswith('-'));summary=any('s'in x[1:] for x in a if x.startswith('-'));ops=[x for x in a if not x.startswith('-')] or ['.'];out=[]
        for t in ops:
            q=self.fs.real(t,self.env)
            if not q.exists():return Result(n,a,r,f"du: cannot access '{t}'\n",False)
            size=lambda p:p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob('*') if f.is_file())
            z=size(q);out.append(f"{self.human(z) if human else max(1,(z+1023)//1024)}\t{t}\n")
            if not summary and q.is_dir():
                for d in sorted(x for x in q.iterdir() if x.is_dir()):z=size(d);out.append(f"{self.human(z) if human else max(1,(z+1023)//1024)}\t{self.fs.virtual(d)}\n")
        return Result(n,a,r,''.join(out),True)
    def cmd_df(self,a,r,n,s):
        human=any('h'in x[1:] for x in a if x.startswith('-'));total=2*1024**3;used=sum(p.stat().st_size for p in self.fs.root.rglob('*') if p.is_file());avail=total-used
        return Result(n,a,r,(f'Filesystem      Size  Used Avail Use% Mounted on\ntrainerfs       2.0G  {self.human(used):>4}  {self.human(avail):>4}   1% /\n' if human else f'Filesystem 1K-blocks Used Available Use% Mounted on\ntrainerfs 2097152 {used//1024} {avail//1024} 1% /\n'),True)
    def cmd_echo(self,a,r,n,s):
        nl='-n' not in a;interp='-e'in a;clean=[x for x in a if x not in ('-n','-e')];v=' '.join(clean)
        if interp:
            try:v=bytes(v,'utf-8').decode('unicode_escape')
            except Exception:pass
        return Result(n,a,r,v+('\n' if nl else ''),True)
    def cmd_printf(self,a,r,n,s):
        if not a:return Result(n,a,r,'printf: missing operand\n',False)
        try:
            fmt=bytes(a[0],'utf-8').decode('unicode_escape'); vals=[int(x) if re.fullmatch(r'-?\d+',x) else x for x in a[1:]];o=fmt%tuple(vals) if '%'in fmt and vals else fmt
            return Result(n,a,r,o,True)
        except Exception as e:return Result(n,a,r,f'printf: {e}\n',False)
    def cmd_tee(self,a,r,n,s):
        append='-a'in a;files=[x for x in a if x!='-a']
        for t in files:
            q=self.fs.real(t,self.env)
            if not q.parent.exists():return Result(n,a,r,f'tee: {t}: No such file or directory\n',False)
            with q.open('a' if append else 'w',encoding='utf-8') as f:f.write(s)
        return Result(n,a,r,s,True)
    def cmd_sed(self,a,r,n,s):
        quiet='-n'in a;inplace='-i'in a;clean=[x for x in a if x not in ('-n','-i')]
        if not clean:return Result(n,a,r,'sed: missing script\n',False)
        script=clean[0];files=clean[1:];src,err,ok=self.read_sources(files,s,'sed');out=err[:];trans=[]
        sub=re.fullmatch(r's(.)(.*?)\1(.*?)\1([gI]*)',script);pr=re.fullmatch(r'(\d+),(\d+)p',script)
        for label,c in src:
            if sub:
                _,old,new,fl=sub.groups()
                try:z=re.sub(old,new,c,count=0 if 'g'in fl else 1,flags=re.I if 'I'in fl else 0)
                except re.error as e:return Result(n,a,r,f'sed: {e}\n',False)
                trans.append((label,z))
                if not quiet and not inplace:out.append(z)
            elif pr:
                lo,hi=map(int,pr.groups());out.append(''.join(c.splitlines(True)[lo-1:hi]));trans.append((label,c))
            else:return Result(n,a,r,"sed: portable mode supports s/old/new/[gI] and -n 'N,Mp'\n",False)
        if inplace:
            if not files:return Result(n,a,r,'sed: no input files for -i\n',False)
            for label,z in trans:self.fs.write(label,z)
        return Result(n,a,r,''.join(out),ok)
    def cmd_awk(self,a,r,n,s):
        d=None;clean=[];i=0
        while i<len(a):
            if a[i]=='-F' and i+1<len(a):d=a[i+1];i+=2
            elif a[i].startswith('-F') and len(a[i])>2:d=a[i][2:];i+=1
            else:clean.append(a[i]);i+=1
        if not clean:return Result(n,a,r,'awk: missing program\n',False)
        m=re.fullmatch(r'\{\s*print\s+\$(\d+)\s*\}',clean[0].strip())
        if not m:return Result(n,a,r,"awk: portable mode supports awk -F, '{print $1}' file\n",False)
        field=int(m.group(1));src,err,ok=self.read_sources(clean[1:],s,'awk');out=err[:]
        for _,c in src:
            for line in c.splitlines():
                p=line.split(d) if d is not None else line.split();out.append((p[field-1] if 1<=field<=len(p) else '')+'\n')
        return Result(n,a,r,''.join(out),ok)
    def cmd_whoami(self,a,r,n,s):return Result(n,a,r,USER+'\n',not a)
    def cmd_id(self,a,r,n,s):return Result(n,a,r,'uid=1000(trainee) gid=1000(training) groups=1000(training)\n',True)
    def cmd_hostname(self,a,r,n,s):return Result(n,a,r,HOST+'\n',True)
    def cmd_uname(self,a,r,n,s):return Result(n,a,r,(f'Linux {HOST} 6.8.0-training #1 SMP x86_64 GNU/Linux\n' if '-a'in a else 'Linux\n'),True)
    def cmd_date(self,a,r,n,s):return Result(n,a,r,datetime.now().astimezone().strftime('%a %b %d %H:%M:%S %Z %Y\n'),True)
    def cmd_env(self,a,r,n,s):
        if a:return Result(n,a,r,'env: command execution form unsupported in portable mode\n',False)
        return Result(n,a,r,''.join(f'{k}={v}\n' for k,v in sorted(self.env.items())),True)
    def cmd_export(self,a,r,n,s):
        if not a:return Result(n,a,r,''.join(f'declare -x {k}="{v}"\n' for k,v in sorted(self.env.items())),True)
        for x in a:
            if '='not in x or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=',x):return Result(n,a,r,f"bash: export: '{x}': not a valid identifier\n",False)
            k,v=x.split('=',1);self.env[k]=v
        return Result(n,a,r,'',True)
    def cmd_unset(self,a,r,n,s):
        for k in a:self.env.pop(k,None)
        return Result(n,a,r,'',True)
    def cmd_history(self,a,r,n,s):return Result(n,a,r,'\n'.join(f'{i+1:5}  {x}' for i,x in enumerate(self.history))+('\n' if self.history else ''),True)
    def cmd_alias(self,a,r,n,s):
        if not a:return Result(n,a,r,''.join(f"alias {k}='{v}'\n" for k,v in sorted(self.aliases.items())),True)
        for x in a:
            if '='not in x:
                if x in self.aliases:return Result(n,a,r,f"alias {x}='{self.aliases[x]}'\n",True)
                return Result(n,a,r,f'bash: alias: {x}: not found\n',False)
            k,v=x.split('=',1);self.aliases[k]=v.strip("'\"")
        return Result(n,a,r,'',True)
    def cmd_unalias(self,a,r,n,s):
        for k in a:
            if k not in self.aliases:return Result(n,a,r,f'bash: unalias: {k}: not found\n',False)
            del self.aliases[k]
        return Result(n,a,r,'',True)
    def cmd_which(self,a,r,n,s):
        if not a:return Result(n,a,r,'',False)
        out=[];ok=True
        for x in a:
            if x in self.commands() or x in self.aliases:out.append(f'/usr/bin/{x}\n')
            elif self.backend.available:
                z=self.backend.run(f'command -v {shlex.quote(x)}',self.fs.cwd,self.env);out.append(z.output);ok&=z.success
            else:ok=False
        return Result(n,a,r,''.join(out),ok)
    def cmd_type(self,a,r,n,s):
        if not a:return Result(n,a,r,'type: missing operand\n',False)
        out=[];ok=True
        for x in a:
            if x in self.aliases:out.append(f"{x} is aliased to `{self.aliases[x]}'\n")
            elif x in self.commands():out.append(f'{x} is /usr/bin/{x}\n')
            else:out.append(f'bash: type: {x}: not found\n');ok=False
        return Result(n,a,r,''.join(out),ok)
    def cmd_ps(self,a,r,n,s):return Result(n,a,r,'    PID TTY          TIME CMD\n   1012 pts/0    00:00:00 bash\n   1094 pts/0    00:00:00 ps\n',True)
    def cmd_clear(self,a,r,n,s):self.clear_screen();return Result(n,a,r,'',True)
    def cmd_true(self,a,r,n,s):return Result(n,a,r,'',True)
    def cmd_false(self,a,r,n,s):return Result(n,a,r,'',False)
    def cmd_commands(self,a,r,n,s):
        c=self.commands();w=max(map(len,c))+2;rows=[''.join(x.ljust(w) for x in c[i:i+5]).rstrip() for i in range(0,len(c),5)];tail='Additional installed commands run inside the isolated Linux container.' if self.backend.available else 'Portable mode supports the full course. The optional container adds more installed Linux commands.'
        return Result(n,a,r,'Built-in trainer commands:\n\n'+'\n'.join(rows)+'\n\n'+tail+'\n',True)
    def cmd_help(self,a,r,n,s):return Result(n,a,r,'Help: run `commands` to list built-ins or `man COMMAND` for command help. Shell operators: | > >> < && || ;\n',True)
    def cmd_man(self,a,r,n,s):
        if not a:return Result(n,a,r,'What manual page do you want?\n',False)
        x=a[0];pages={
            'ls':'LS(1)\n  ls [OPTIONS] [PATH...]\n  -l details, -a include hidden files, -h readable sizes, -t sort by modified time, -r reverse order, -R recursive, -F add type markers. Flags can be combined, for example: ls -ltr.\n',
            'grep':'GREP(1)\n  grep [OPTIONS] PATTERN [FILE...]\n  -i ignore case, -n show line numbers, -v show non-matching lines, -r search directories recursively, -c count matches, -l show matching filenames, -E extended regular expressions, -w whole words.\n',
            'find':"FIND(1)\n  find [PATH] [-name PATTERN] [-type f|d|l] [-maxdepth N] [-mindepth N]\n",
            'chmod':'CHMOD(1)\n  chmod MODE FILE...\n  Examples: chmod +x script.sh ; chmod 755 script.sh ; chmod u+rw,go-r file\n',
            'cp':'CP(1)\n  cp [OPTIONS] SOURCE... DEST\n  -r/-R copy directories recursively, -p preserve file attributes, -v show copied files, -f overwrite when needed.\n',
            'rm':'RM(1)\n  rm [OPTIONS] FILE...\n  -r/-R remove directories recursively, -f do not prompt for missing files, -v show removed files. Check the path before running rm.\n',
            'sed':"SED(1)\n  Examples: sed 's/old/new/' file ; sed -i 's/old/new/g' file ; sed -n '2,5p' file\n",
            'awk':"AWK(1)\n  Portable examples: awk '{print $1}' file ; awk -F, '{print $2}' file.csv\n"}
        if x in pages:return Result(n,a,r,pages[x],True)
        if x in self.commands():return Result(n,a,r,f'{x.upper()}(1)\n  Built-in trainer command. Use Command Guide for examples.\n',True)
        if self.backend.available:return self.backend.run(f'{shlex.quote(x)} --help',self.fs.cwd,self.env)
        return Result(n,a,r,f'No manual entry for {x}\n',False)
    def cmd_vi(self,a,r,n,s):return self.editor(a,r,n)
    def cmd_vim(self,a,r,n,s):return self.editor(a,r,n)
    def cmd_gvim(self,a,r,n,s):return self.editor(a,r,n)
    def cmd_nano(self,a,r,n,s):return self.editor(a,r,n)
    def editor(self,a,r,n):
        if len(a)!=1:return Result(n,a,r,f'{n}: expected one file path\n',False)
        vp=self.fs.resolve(a[0],self.env);q=self.fs.real(vp,self.env)
        if q.exists() and q.is_dir():return Result(n,a,r,f'{n}: {a[0]} is a directory\n',False)
        if not q.parent.exists():return Result(n,a,r,f'{n}: {a[0]}: No such file or directory\n',False)
        self.open_editor(vp,n);return Result(n,a,r,f'Opening {n} editor for {vp}\n',True,{'editor':n,'path':vp})

class RoundedFrame(tk.Canvas):
    """Small canvas-backed card that preserves the original dark rounded-card aesthetic."""
    def __init__(self,master,fill=SURFACE,outer=BG,radius=16,border=BORDER,width=200,height=100):
        super().__init__(master,bg=outer,highlightthickness=0,bd=0,width=width,height=height)
        self.fill,self.radius,self.border=fill,radius,border
        self.content=tk.Frame(self,bg=fill,bd=0,highlightthickness=0)
        self.win=self.create_window(7,7,anchor='nw',window=self.content)
        self.bind('<Configure>',self._redraw)
    def _redraw(self,e=None):
        self.delete('card'); w=max(4,self.winfo_width()); h=max(4,self.winfo_height()); r=min(self.radius,(w-4)//2,(h-4)//2)
        # Tk's smoothed polygon is compact and renders cleanly on Windows/macOS/Linux.
        pts=[2+r,2,w-2-r,2,w-2,2,w-2,2+r,w-2,h-2-r,w-2,h-2,w-2-r,h-2,2+r,h-2,2,h-2,2,h-2-r,2,2+r,2,2]
        self.create_polygon(pts,smooth=True,splinesteps=24,fill=self.fill,outline=self.border,width=1,tags='card')
        self.coords(self.win,8,8); self.itemconfigure(self.win,width=max(1,w-16),height=max(1,h-16)); self.tag_lower('card')

class SeamlessScrollbar(tk.Canvas):
    """A trackless overlay scrollbar drawn entirely with Tk Canvas.

    It never asks macOS/Windows/Linux to render a native scrollbar, and it never
    paints a separate trough. Only a slim muted thumb is visible when scrolling
    is possible, so the control visually merges into the panel underneath it.
    """
    def __init__(self, master, command, *, orient='vertical', track_color=SURFACE3,
                 thumb_color='#294761', active_color='#3A6688', thickness=8):
        self.orient = orient
        self.command = command
        self.track_color = track_color
        self.thumb_color = thumb_color
        self.active_color = active_color
        self.first = 0.0
        self.last = 1.0
        self.dragging = False
        self.drag_offset = 0.0
        self.hovering = False
        kw = dict(bg=track_color, highlightthickness=0, bd=0, relief='flat', takefocus=0)
        if orient == 'vertical':
            kw.update(width=thickness)
        else:
            kw.update(height=thickness)
        super().__init__(master, **kw)
        self.bind('<Configure>', lambda e: self._redraw())
        self.bind('<Button-1>', self._mouse_down)
        self.bind('<B1-Motion>', self._mouse_drag)
        self.bind('<ButtonRelease-1>', self._mouse_up)
        self.bind('<Motion>', self._mouse_move)
        self.bind('<Leave>', self._mouse_leave)
        self.bind('<MouseWheel>', self._mouse_wheel)
        self.bind('<Button-4>', lambda e: self._scroll_units(-3))
        self.bind('<Button-5>', lambda e: self._scroll_units(3))

    def set(self, first, last):
        try:
            self.first = max(0.0, min(1.0, float(first)))
            self.last = max(self.first, min(1.0, float(last)))
        except (TypeError, ValueError):
            self.first, self.last = 0.0, 1.0
        self._redraw()

    def _axis_length(self):
        return max(1, self.winfo_height() if self.orient == 'vertical' else self.winfo_width())

    def _cross_length(self):
        return max(1, self.winfo_width() if self.orient == 'vertical' else self.winfo_height())

    def _thumb_bounds(self):
        if self.last - self.first >= 0.999:
            return None
        length = self._axis_length()
        raw_top = self.first * length
        raw_bottom = self.last * length
        thumb_len = max(28.0, raw_bottom - raw_top)
        thumb_len = min(float(length), thumb_len)
        max_top = max(0.0, length - thumb_len)
        top = min(max_top, raw_top)
        return top, top + thumb_len

    def _pointer_axis(self, event):
        return float(event.y if self.orient == 'vertical' else event.x)

    def _inside_thumb(self, pos):
        bounds = self._thumb_bounds()
        return bool(bounds and bounds[0] <= pos <= bounds[1])

    def _redraw(self):
        # Intentionally draw NO trough/track. The canvas background exactly
        # matches the content beneath it; only the thumb exists visually.
        self.delete('all')
        bounds = self._thumb_bounds()
        if not bounds:
            return
        top, bottom = bounds
        cross = self._cross_length()
        color = self.active_color if (self.dragging or self.hovering) else self.thumb_color
        # Keep the thumb narrow even when the overlay hit area is wider.
        visual = max(3, min(5, cross - 2))
        inset = max(1, (cross - visual) // 2)
        radius = max(1, visual // 2)
        if self.orient == 'vertical':
            x1, x2 = inset, inset + visual
            self.create_rectangle(x1, top + radius, x2, bottom - radius, fill=color, outline=color)
            self.create_oval(x1, top, x2, top + 2 * radius, fill=color, outline=color)
            self.create_oval(x1, bottom - 2 * radius, x2, bottom, fill=color, outline=color)
        else:
            y1, y2 = inset, inset + visual
            self.create_rectangle(top + radius, y1, bottom - radius, y2, fill=color, outline=color)
            self.create_oval(top, y1, top + 2 * radius, y2, fill=color, outline=color)
            self.create_oval(bottom - 2 * radius, y1, bottom, y2, fill=color, outline=color)

    def _mouse_down(self, event):
        pos = self._pointer_axis(event)
        bounds = self._thumb_bounds()
        if not bounds:
            return 'break'
        top, bottom = bounds
        if top <= pos <= bottom:
            self.dragging = True
            self.drag_offset = pos - top
        else:
            direction = -1 if pos < top else 1
            self.command('scroll', direction, 'pages')
        self._redraw()
        return 'break'

    def _mouse_drag(self, event):
        if not self.dragging:
            return 'break'
        bounds = self._thumb_bounds()
        if not bounds:
            return 'break'
        thumb_len = bounds[1] - bounds[0]
        travel = max(1.0, self._axis_length() - thumb_len)
        new_top = min(travel, max(0.0, self._pointer_axis(event) - self.drag_offset))
        self.command('moveto', new_top / travel)
        return 'break'

    def _mouse_up(self, event):
        self.dragging = False
        self._redraw()
        return 'break'

    def _mouse_move(self, event):
        hovering = self._inside_thumb(self._pointer_axis(event))
        if hovering != self.hovering:
            self.hovering = hovering
            self._redraw()

    def _mouse_leave(self, event):
        if not self.dragging and self.hovering:
            self.hovering = False
            self._redraw()

    def _scroll_units(self, units):
        self.command('scroll', units, 'units')
        return 'break'

    def _mouse_wheel(self, event):
        if not getattr(event,'delta',0):
            return 'break'
        return self._scroll_units(-3 if event.delta > 0 else 3)

class LinuxTrainerApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_TITLE); self.geometry('1580x940'); self.minsize(1280,760); self.configure(bg=BG)
        self.fs=VirtualFS(); self.shell=Shell(self.fs,self.open_editor,self.clear_terminal)
        self.lesson_index=0; self.lessons=self.make_lessons(); self.history_index=None; self._scratch_seen=False
        self._setup_style(); self._build_ui(); self._welcome(); self._prompt(); self.refresh_sidebar()
        self.protocol('WM_DELETE_WINDOW',self.close)

    def _setup_style(self):
        st=ttk.Style(self)
        try: st.theme_use('clam')
        except tk.TclError: pass
        st.configure('Lab.TButton',background=BTN,foreground=TEXT,borderwidth=0,focusthickness=0,padding=(14,10),font=('Segoe UI',10,'bold'))
        st.map('Lab.TButton',background=[('active',BTN_ACTIVE),('pressed',BTN_ACTIVE)])

    def card(self,parent,**grid):
        height=grid.pop('height',120); fill=grid.pop('fill',SURFACE); radius=grid.pop('radius',16); outer=parent.cget('bg')
        c=RoundedFrame(parent,fill=fill,outer=outer,radius=radius,height=height); c.grid(**grid); return c.content

    def _build_ui(self):
        self.rowconfigure(1,weight=1); self.columnconfigure(0,weight=1)
        top=tk.Frame(self,bg='#07111F',height=66); top.grid(row=0,column=0,sticky='ew'); top.grid_propagate(False); top.columnconfigure(1,weight=1)
        tk.Label(top,text='LOCKHEED MARTIN • LINUX TERMINAL LAB',bg='#07111F',fg=TEXT,font=('Segoe UI',16,'bold')).grid(row=0,column=0,sticky='w',padx=22,pady=18)
        self.backend_chip=tk.Label(top,text='',bg='#123B63',fg=ACCENT,font=('Segoe UI',10,'bold'),padx=13,pady=7)
        self.backend_chip.grid(row=0,column=1,sticky='e',padx=22,pady=13)

        body=tk.Frame(self,bg=BG); body.grid(row=1,column=0,sticky='nsew',padx=16,pady=16); body.rowconfigure(0,weight=1); body.columnconfigure(0,weight=5); body.columnconfigure(1,weight=3)
        left=self.card(body,row=0,column=0,sticky='nsew',padx=(0,10)); left.rowconfigure(2,weight=1); left.columnconfigure(0,weight=1)
        head=tk.Frame(left,bg=SURFACE2,height=82); head.grid(row=0,column=0,sticky='ew'); head.grid_propagate(False); head.columnconfigure(0,weight=1)
        tk.Label(head,text='Linux Workstation',bg=SURFACE2,fg=TEXT,font=('Segoe UI',21,'bold')).grid(row=0,column=0,sticky='w',padx=20,pady=(13,0))
        tk.Label(head,text='Practice Linux commands in a safe, persistent training filesystem',bg=SURFACE2,fg=SOFT,font=('Segoe UI',10)).grid(row=1,column=0,sticky='w',padx=20,pady=(3,0))
        status=tk.Frame(left,bg=SURFACE,height=51); status.grid(row=1,column=0,sticky='ew',padx=18,pady=(10,8)); status.grid_propagate(False); status.columnconfigure(1,weight=1)
        tk.Label(status,text=f'{USER}@{HOST}',bg='#113728',fg='#D4FFE7',font=('Segoe UI',10,'bold'),padx=13,pady=7).grid(row=0,column=0,sticky='w',pady=7)
        self.module_chip=tk.Label(status,text='',bg='#14304A',fg='#BEE5FF',font=('Segoe UI',10,'bold'),padx=13,pady=7); self.module_chip.grid(row=0,column=1,sticky='e',pady=7)

        termwrap=tk.Frame(left,bg=SURFACE); termwrap.grid(row=2,column=0,sticky='nsew',padx=18); termwrap.rowconfigure(0,weight=1); termwrap.columnconfigure(0,weight=1)
        self.terminal=tk.Text(termwrap,wrap='word',font=('Cascadia Mono',13),bg=TERM_BG,fg=TERM_FG,insertbackground=ACCENT2,relief='flat',bd=0,highlightthickness=0,highlightbackground=TERM_BG,highlightcolor=TERM_BG,padx=18,pady=16,selectbackground='#163558')
        self.terminal.grid(row=0,column=0,sticky='nsew')
        sb=SeamlessScrollbar(termwrap,command=self.terminal.yview,track_color=TERM_BG,thumb_color='#294761',active_color='#3A6688',thickness=8); sb.place(relx=1.0,rely=0.0,relheight=1.0,anchor='ne'); self.terminal.configure(yscrollcommand=sb.set)
        for tag,color in [('banner',SOFT),('system','#8BB7FF'),('error',ERROR),('success',SUCCESS),('prompt',ACCENT2),('lesson',ACCENT)]: self.terminal.tag_configure(tag,foreground=color)
        self.terminal.bind('<Return>',self.on_enter); self.terminal.bind('<BackSpace>',self.on_backspace); self.terminal.bind('<Left>',self.guard_cursor); self.terminal.bind('<Home>',self.home_key); self.terminal.bind('<Up>',self.history_up); self.terminal.bind('<Down>',self.history_down); self.terminal.bind('<Tab>',self.tab_complete); self.terminal.bind('<Control-l>',self.ctrl_l); self.terminal.bind('<Button-1>',lambda e:self.after(1,self.ensure_cursor))
        self.footer=tk.Label(left,text='Shortcuts: Tab complete • ↑/↓ history • Ctrl+L clear • man <command> help • commands show built-ins',bg=SURFACE,fg=MUTED,font=('Segoe UI',9),anchor='w'); self.footer.grid(row=3,column=0,sticky='ew',padx=20,pady=(9,13))

        right=tk.Frame(body,bg=BG); right.grid(row=0,column=1,sticky='nsew'); right.columnconfigure(0,weight=1); right.rowconfigure(1,weight=2); right.rowconfigure(2,weight=3)
        prog=self.card(right,row=0,column=0,sticky='ew',height=150); prog.columnconfigure(0,weight=1)
        tk.Label(prog,text='Learning Path',bg=SURFACE,fg=TEXT,font=('Segoe UI',20,'bold')).grid(row=0,column=0,sticky='w',padx=18,pady=(12,0))
        self.progress_text=tk.Label(prog,text='',bg=SURFACE,fg=ACCENT,font=('Segoe UI',10,'bold')); self.progress_text.grid(row=1,column=0,sticky='w',padx=18,pady=(5,0))
        self.progress=tk.Canvas(prog,height=10,bg=SURFACE,highlightthickness=0); self.progress.grid(row=2,column=0,sticky='ew',padx=18,pady=(10,13)); self.progress.bind('<Configure>',lambda e:self.draw_progress())

        lesson=self.card(right,row=1,column=0,sticky='nsew',pady=(10,10),height=330); lesson.rowconfigure(2,weight=1); lesson.columnconfigure(0,weight=1)
        tk.Label(lesson,text='Current Lesson',bg=SURFACE,fg=TEXT,font=('Segoe UI',14,'bold')).grid(row=0,column=0,sticky='w',padx=18,pady=(12,0))
        self.lesson_title=tk.Label(lesson,text='',bg=SURFACE,fg=ACCENT2,font=('Segoe UI',11,'bold'),anchor='w',justify='left'); self.lesson_title.grid(row=1,column=0,sticky='ew',padx=18,pady=(4,7))
        lwrap=tk.Frame(lesson,bg=SURFACE3,highlightthickness=1,highlightbackground=BORDER); lwrap.grid(row=2,column=0,sticky='nsew',padx=18,pady=(0,14)); lwrap.rowconfigure(0,weight=1); lwrap.columnconfigure(0,weight=1)
        self.lesson_box=tk.Text(lwrap,wrap='word',bg=SURFACE3,fg=TEXT,relief='flat',bd=0,highlightthickness=0,font=('Segoe UI',11),padx=12,pady=10,spacing3=3); self.lesson_box.grid(row=0,column=0,sticky='nsew'); lesson_sb=SeamlessScrollbar(lwrap,command=self.lesson_box.yview,track_color=SURFACE3,thumb_color='#294761',active_color='#3A6688',thickness=8); lesson_sb.place(relx=1.0,rely=0.0,relheight=1.0,anchor='ne'); self.lesson_box.configure(yscrollcommand=lesson_sb.set); self.lesson_box.tag_configure('label',foreground=ACCENT,font=('Segoe UI',10,'bold')); self.lesson_box.tag_configure('example',foreground=SOFT,font=('Cascadia Mono',10)); self.lesson_box.configure(state='disabled')

        cmap=self.card(right,row=2,column=0,sticky='nsew',height=340); cmap.rowconfigure(1,weight=1); cmap.columnconfigure(0,weight=1)
        tk.Label(cmap,text='Course Map',bg=SURFACE,fg=TEXT,font=('Segoe UI',14,'bold')).grid(row=0,column=0,sticky='w',padx=18,pady=(12,7))
        mwrap=tk.Frame(cmap,bg=SURFACE3,highlightthickness=1,highlightbackground=BORDER); mwrap.grid(row=1,column=0,sticky='nsew',padx=18,pady=(0,13)); mwrap.rowconfigure(0,weight=1); mwrap.columnconfigure(0,weight=1)
        self.map_box=tk.Text(mwrap,wrap='word',bg=SURFACE3,fg=SOFT,relief='flat',bd=0,highlightthickness=0,font=('Segoe UI',10),padx=11,pady=9,spacing3=4); self.map_box.grid(row=0,column=0,sticky='nsew'); msb=SeamlessScrollbar(mwrap,command=self.map_box.yview,track_color=SURFACE3,thumb_color='#294761',active_color='#3A6688',thickness=8); msb.place(relx=1.0,rely=0.0,relheight=1.0,anchor='ne'); self.map_box.configure(yscrollcommand=msb.set); self.map_box.tag_configure('done',foreground=SUCCESS,font=('Segoe UI',10,'bold')); self.map_box.tag_configure('current',foreground=TEXT,font=('Segoe UI',10,'bold')); self.map_box.tag_configure('module',foreground=ACCENT,font=('Segoe UI',9,'bold')); self.map_box.configure(state='disabled')
        btns=tk.Frame(right,bg=BG); btns.grid(row=3,column=0,sticky='ew',pady=(10,0)); [btns.columnconfigure(i,weight=1) for i in range(3)]
        ttk.Button(btns,text='Hint',style='Lab.TButton',command=self.show_hint).grid(row=0,column=0,sticky='ew',padx=(0,5)); ttk.Button(btns,text='Command Guide',style='Lab.TButton',command=self.show_guide).grid(row=0,column=1,sticky='ew',padx=5); ttk.Button(btns,text='Reset Lab',style='Lab.TButton',command=self.reset_lab).grid(row=0,column=2,sticky='ew',padx=(5,0))

    def _write(self,text,tag=None):
        if tag:self.terminal.insert('end',text,tag)
        else:self.terminal.insert('end',text)
        self.terminal.see('end')

    def _welcome(self):
        mode=f"REAL LINUX BACKEND: {self.shell.backend.runtime} / {self.shell.backend.image}" if self.shell.backend.available else 'PORTABLE SANDBOX MODE'
        self._write('Linux Terminal Lab\n──────────────────\n\n','lesson')
        self._write('Complete the task shown on the right. Any valid supported command that completes the task is accepted.\n','banner')
        self._write('Files and changes stay in place as you move through the lessons.\n')
        self._write('Examples are optional. Normal Linux syntax works, including flags such as ls -ltr, relative paths, pipes, redirects, aliases, and Tab completion.\n')
        self._write('vi, vim, gvim, and nano open the lab editor. Save the file there, then continue in the terminal.\n\n')
        self._write(f'Backend: {mode}\n\n','system')

    def prompt_text(self):
        p=self.fs.cwd; show='~' if p==HOME else ('~'+p[len(HOME):] if p.startswith(HOME+'/') else p)
        return f'{USER}@{HOST}:{show}$ '
    def _prompt(self):
        st=self.terminal.index('end-1c'); self.terminal.insert('end',self.prompt_text()); en=self.terminal.index('end-1c'); self.terminal.tag_add('prompt',st,en); self.terminal.mark_set('input_start','insert'); self.terminal.mark_gravity('input_start','left'); self.terminal.focus_set()
    def current_input(self): return self.terminal.get('input_start','end-1c')
    def replace_input(self,s): self.terminal.delete('input_start','end-1c'); self.terminal.insert('end',s)
    def on_enter(self,e=None):
        cmd=self.current_input().strip(); self._write('\n'); self.history_index=None
        if cmd:
            res=self.shell.run(cmd)
            if res.output:
                is_diff=(res.name=='diff' and bool(res.meta.get('different'))); self._write(res.output,'error' if (not res.success and not is_diff) else None)
            self.evaluate(res)
        self._prompt(); return 'break'
    def on_backspace(self,e): return 'break' if self.terminal.compare('insert','<=','input_start') else None
    def guard_cursor(self,e): return 'break' if self.terminal.compare('insert','<=','input_start') else None
    def home_key(self,e): self.terminal.mark_set('insert','input_start'); return 'break'
    def ensure_cursor(self):
        if self.terminal.compare('insert','<','input_start'): self.terminal.mark_set('insert','end-1c')
    def history_up(self,e):
        h=self.shell.history
        if not h:return 'break'
        self.history_index=len(h)-1 if self.history_index is None else max(0,self.history_index-1); self.replace_input(h[self.history_index]); return 'break'
    def history_down(self,e):
        if self.history_index is None:return 'break'
        self.history_index+=1
        if self.history_index>=len(self.shell.history):self.history_index=None;self.replace_input('')
        else:self.replace_input(self.shell.history[self.history_index])
        return 'break'
    def ctrl_l(self,e): self.clear_terminal(); self._prompt(); return 'break'
    def clear_terminal(self):
        if hasattr(self,'terminal'): self.terminal.delete('1.0','end')

    def tab_complete(self,e):
        text=self.current_input(); m=re.search(r'(^|\s)([^\s]*)$',text); token=m.group(2) if m else ''; prefix=text[:-len(token)] if token else text
        choices=[]
        if not prefix.strip() and '/' not in token:
            choices=[c for c in self.shell.commands() if c.startswith(token)]
        if not choices:
            expanded=token
            if '/' in expanded: base,partial=expanded.rsplit('/',1); base=base or '/'
            else: base,partial='.',expanded
            try:
                q=self.fs.real(base,self.shell.env)
                if q.is_dir():
                    for x in sorted(q.iterdir(),key=lambda z:(not z.is_dir(),z.name.lower())):
                        if x.name.startswith(partial):
                            lead=(token.rsplit('/',1)[0]+'/' if '/' in token else ''); choices.append(lead+x.name+('/' if x.is_dir() else ' '))
            except Exception: pass
        if not choices:return 'break'
        if len(choices)==1:self.replace_input(prefix+choices[0]);return 'break'
        common=os.path.commonprefix(choices)
        if len(common)>len(token):self.replace_input(prefix+common);return 'break'
        self._write('\n'+'  '.join(choices)+'\n','system'); self._prompt(); self.terminal.insert('end',text); return 'break'

    @staticmethod
    def _r(res,name): return bool(res and res.name==name and res.success)
    def file_contains(self,p,*needles):
        try:
            txt=self.fs.read(p); return all(x in txt for x in needles)
        except Exception:return False
    def executable(self,p):
        try:return bool(self.fs.real(p).stat().st_mode & stat.S_IXUSR)
        except Exception:return False

    def make_lessons(self):
        L=[]; add=L.append
        add(Lesson('01 • Basics','Show your current directory (pwd)','`pwd` prints the full path of the directory you are currently in.','Run `pwd` to show your current directory.',('pwd',),'Run `pwd`.',lambda a,r:a._r(r,'pwd') and HOME in r.output))
        add(Lesson('01 • Basics','List files and folders (ls)','`ls` shows the files and folders in a directory. Options change how the list is displayed.','List the contents of your home directory.',('ls','ls -l','ls -ltr','ll'),"Run `ls`. `ls -l` shows details. `ls -ltr` sorts by modified time and reverses the order. `ll` is a lab alias for a detailed listing.",lambda a,r:a._r(r,'ls') and 'projects' in r.output and 'scripts' in r.output))
        add(Lesson('01 • Basics','Show hidden files (ls -a)','`ls -a` also shows names that begin with a dot, such as `.bashrc`.','List your home directory and include hidden files.',('ls -a','ls -la'),"Use `ls -a`. `ls -la` adds the long-list format.",lambda a,r:a._r(r,'ls') and '.bashrc' in r.output))
        add(Lesson('01 • Basics','Change directories (cd)','`cd` moves you to another directory.','Change to `/home/trainee/projects/atlas`.',('cd ~/projects/atlas','cd projects/atlas','cd /home/trainee/projects/atlas'),"From your home directory, `cd projects/atlas` works.",lambda a,r:r is not None and r.name=='cd' and a.fs.cwd=='/home/trainee/projects/atlas'))
        add(Lesson('01 • Basics','Return to your home directory (cd)','Running `cd` with no path returns you to your home directory.','Return to `/home/trainee`.',('cd','cd ~','cd /home/trainee'),"Run `cd` with no arguments.",lambda a,r:r is not None and r.name=='cd' and a.fs.cwd==HOME))

        add(Lesson('02 • Files & Folders','Create folders (mkdir -p)','`mkdir` creates directories. `-p` also creates any missing parent directories.','Create `/home/trainee/workspace/onboarding/reports`.',('mkdir -p workspace/onboarding/reports','mkdir -p ~/workspace/onboarding/reports'),"Use `mkdir -p` followed by the full directory path.",lambda a,r:a.fs.is_dir('/home/trainee/workspace/onboarding/reports')))
        add(Lesson('02 • Files & Folders','Copy a file (cp)','`cp` copies a file and leaves the original in place.','Copy `/etc/training/service.conf` into `~/workspace/onboarding/`.',('cp /etc/training/service.conf ~/workspace/onboarding/','cp -v /etc/training/service.conf workspace/onboarding/'),"Use `cp SOURCE DESTINATION`.",lambda a,r:a.fs.is_file('/home/trainee/workspace/onboarding/service.conf') and a.file_contains('/home/trainee/workspace/onboarding/service.conf','service_name=atlas')))
        add(Lesson('02 • Files & Folders','Rename a file (mv)','`mv` renames a file or moves it to another directory.','Rename `~/workspace/onboarding/service.conf` to `atlas.conf`.',('mv ~/workspace/onboarding/service.conf ~/workspace/onboarding/atlas.conf',),"Use `mv OLD_NAME NEW_NAME`.",lambda a,r:a.fs.is_file('/home/trainee/workspace/onboarding/atlas.conf') and not a.fs.exists('/home/trainee/workspace/onboarding/service.conf')))
        add(Lesson('02 • Files & Folders','Create an empty file (touch)','`touch` creates an empty file when the file does not already exist.','Create `~/workspace/onboarding/scratch.tmp`.',('touch ~/workspace/onboarding/scratch.tmp',),"Use `touch FILE`.",lambda a,r:a.fs.is_file('/home/trainee/workspace/onboarding/scratch.tmp')))
        add(Lesson('02 • Files & Folders','Delete a file (rm)','`rm` deletes files. Check the path before you run it.','Delete `~/workspace/onboarding/scratch.tmp`. Keep the onboarding directory.',('rm ~/workspace/onboarding/scratch.tmp','rm -v workspace/onboarding/scratch.tmp'),"Run `rm` on `scratch.tmp` only.",lambda a,r:not a.fs.exists('/home/trainee/workspace/onboarding/scratch.tmp') and a.fs.is_dir('/home/trainee/workspace/onboarding')))

        add(Lesson('03 • View & Search','Read a file (cat)','`cat` prints a text file to the terminal.','Display `~/projects/atlas/README.md`.',('cat ~/projects/atlas/README.md',),"Use `cat FILE`.",lambda a,r:a._r(r,'cat') and '# Atlas Training Service' in r.output))
        add(Lesson('03 • View & Search','Show the last lines of a file (tail)','`tail` shows the end of a file.','Display the last 3 lines of `/var/log/training/app.log`.',('tail -n 3 /var/log/training/app.log','tail -3 /var/log/training/app.log'),"Use `tail -n 3 FILE`.",lambda a,r:a._r(r,'tail') and len([x for x in r.output.splitlines() if x.strip()])==3 and 'health check passed' in r.output))
        add(Lesson('03 • View & Search','Search text in a file (grep -n)','`grep` finds matching text. `-n` also prints the matching line numbers.','Find every `ERROR` line in `/var/log/training/app.log` and show line numbers.',('grep -n ERROR /var/log/training/app.log','grep -n "ERROR" /var/log/training/app.log'),"Use `grep -n PATTERN FILE`.",lambda a,r:a._r(r,'grep') and r.meta.get('matches')==3 and r.meta.get('line_numbers') and '4:' in r.output))
        add(Lesson('03 • View & Search','Count lines (wc -l)','`wc -l` counts the number of lines in a file or command output.','Count the lines in `/opt/training/data/systems.csv`.',('wc -l /opt/training/data/systems.csv',),"Use `wc -l FILE`.",lambda a,r:a._r(r,'wc') and re.search(r'\b6\b',r.output) is not None))

        add(Lesson('04 • Pipes & Redirects','Send output to another command (|)','A pipe (`|`) sends the output of one command into the next command.','Use a pipe to count the `ERROR` lines in `/var/log/training/app.log`.',('grep ERROR /var/log/training/app.log | wc -l',),"Pipe `grep` into `wc -l`.",lambda a,r:a._r(r,'wc') and '|' in r.raw and re.search(r'\b3\b',r.output) is not None))
        add(Lesson('04 • Pipes & Redirects','Write output to a file (>)','`>` writes command output to a file and replaces the file if it already exists.','Write the `ERROR` lines from `app.log` to `~/workspace/onboarding/reports/errors.txt`.',('grep ERROR /var/log/training/app.log > ~/workspace/onboarding/reports/errors.txt',),"Put `> FILE` after the command.",lambda a,r:a.fs.is_file('/home/trainee/workspace/onboarding/reports/errors.txt') and a.fs.read('/home/trainee/workspace/onboarding/reports/errors.txt').count('ERROR')==3))
        add(Lesson('04 • Pipes & Redirects','Append output to a file (>>)','`>>` adds output to the end of a file without replacing its current contents.','Append the exact line `Reviewed by trainee` to `errors.txt`.',("echo 'Reviewed by trainee' >> ~/workspace/onboarding/reports/errors.txt",),"Use `>>` instead of `>`.",lambda a,r:a.file_contains('/home/trainee/workspace/onboarding/reports/errors.txt','Reviewed by trainee')))

        add(Lesson('05 • Find & Permissions','Find files by name (find)','`find` searches through directories and subdirectories.','Find every `*.conf` file under your home directory.',("find ~ -name '*.conf'", "find /home/trainee -type f -name '*.conf'"),"Use `find ~ -name '*.conf'`. Keep `*.conf` in quotes.",lambda a,r:a._r(r,'find') and 'dev.conf' in r.output and 'trainer.conf' in r.output))
        add(Lesson('05 • Find & Permissions','Make a script executable (chmod +x)','`chmod +x` gives a file execute permission so it can be run as a program or script.','Add execute permission to `~/scripts/report.sh`.',('chmod +x ~/scripts/report.sh','chmod 755 ~/scripts/report.sh'),"Use `chmod +x FILE`.",lambda a,r:a.executable('/home/trainee/scripts/report.sh')))
        add(Lesson('05 • Find & Permissions','Show file details (stat)','`stat` shows a file\'s permissions, size, and timestamps.','Run `stat` on `~/scripts/report.sh`.',('stat ~/scripts/report.sh',),"Use `stat FILE`.",lambda a,r:a._r(r,'stat') and 'report.sh' in r.output and 'Access:' in r.output))

        add(Lesson('06 • Edit & Compare','Edit a configuration file (vim or nano)','Use a text editor when you need to change file contents directly.','Open `~/workspace/onboarding/atlas.conf`. Change `enabled=false` to `enabled=true` and `owner=unset` to `owner=trainee`, then save.',('vim ~/workspace/onboarding/atlas.conf','vi ~/workspace/onboarding/atlas.conf','nano ~/workspace/onboarding/atlas.conf'),"Open the file, make both changes, then save with Ctrl+S or `:wq` in the lab editor.",lambda a,r:a.file_contains('/home/trainee/workspace/onboarding/atlas.conf','enabled=true','owner=trainee')))
        add(Lesson('06 • Edit & Compare','Compare two files (diff -u)','`diff -u` shows the lines that differ between two text files.','Compare your `atlas.conf` with `/opt/training/examples/service.conf`.',('diff -u ~/workspace/onboarding/atlas.conf /opt/training/examples/service.conf',),"Use `diff -u FILE1 FILE2`. Output is expected when the files differ.",lambda a,r:bool(r and r.name=='diff' and r.meta.get('different') and ('---' in r.output or '@@' in r.output))))
        add(Lesson('06 • Edit & Compare','Replace text in a file (sed -i)','`sed -i` can replace text directly inside a file.','Change `log_level=INFO` to `log_level=WARN` in `~/workspace/onboarding/atlas.conf`.',("sed -i 's/log_level=INFO/log_level=WARN/' ~/workspace/onboarding/atlas.conf",),"Use `sed -i 's/OLD/NEW/' FILE`.",lambda a,r:a.file_contains('/home/trainee/workspace/onboarding/atlas.conf','log_level=WARN')))

        add(Lesson('07 • CSV & Text','Print a CSV column (cut)','`cut` extracts fields from text that uses a consistent delimiter.','Print column 1 (`hostname`) from `/opt/training/data/systems.csv`.',("cut -d, -f1 /opt/training/data/systems.csv",),"Use comma as the delimiter (`-d,`) and field 1 (`-f1`).",lambda a,r:a._r(r,'cut') and 'atlas-dev-01' in r.output and 'atlas-prod-02' in r.output))
        add(Lesson('07 • CSV & Text','Print a CSV column (awk)','`awk` can split each line into fields and print the fields you choose.','Print column 2 (`environment`) from `systems.csv` using `awk`.',("awk -F, '{print $2}' /opt/training/data/systems.csv",),"Set comma as the field separator with `-F,`, then print `$2`.",lambda a,r:a._r(r,'awk') and all(x in r.output.splitlines() for x in ('dev','qa','prod'))))
        add(Lesson('07 • CSV & Text','Sort and remove duplicates (sort -u)','`sort -u` sorts lines and removes duplicates.','Use a pipeline to print a sorted, unique list of environments from `systems.csv`.',("cut -d, -f2 /opt/training/data/systems.csv | sort -u", "awk -F, '{print $2}' /opt/training/data/systems.csv | sort -u"),"Extract column 2, pipe it into `sort -u`.",lambda a,r:a._r(r,'sort') and '|' in r.raw and all(x in r.output.splitlines() for x in ('dev','qa','prod'))))

        add(Lesson('08 • Shell','Set an environment variable (export)','`export` sets a variable for the current shell and commands started from it.','Set `LAB_OWNER=trainee`, then print the variable.',('export LAB_OWNER=trainee','echo $LAB_OWNER','export LAB_OWNER=trainee && echo $LAB_OWNER'),"Run `export LAB_OWNER=trainee`, then `echo $LAB_OWNER`.",lambda a,r:a.shell.env.get('LAB_OWNER')=='trainee' and r is not None and 'trainee' in r.output))
        add(Lesson('08 • Shell','Show command history (history)','`history` lists commands you entered earlier in the session.','Display your command history.',('history',),"Run `history`.",lambda a,r:a._r(r,'history') and len(r.output.splitlines())>=10))

        add(Lesson('09 • Final Practice','Build the audit folder','Use the commands from earlier lessons together in one small workflow.','Create `~/workspace/audit/` with three files: `service.conf` copied from your edited `atlas.conf`; `errors.log` containing the three `ERROR` lines from `app.log`; and an executable copy of `report.sh`. When finished, run a long `ls` listing of the audit directory.',('mkdir -p ~/workspace/audit','cp ~/workspace/onboarding/atlas.conf ~/workspace/audit/service.conf','grep ERROR /var/log/training/app.log > ~/workspace/audit/errors.log','cp ~/scripts/report.sh ~/workspace/audit/report.sh','chmod +x ~/workspace/audit/report.sh','ls -ltr ~/workspace/audit'),"Create the folder, copy the config and script, create `errors.log`, make the copied script executable, then run `ls -l` or `ls -ltr` on the audit directory.",lambda a,r:a.fs.is_file('/home/trainee/workspace/audit/service.conf') and a.fs.is_file('/home/trainee/workspace/audit/errors.log') and a.fs.read('/home/trainee/workspace/audit/errors.log').count('ERROR')==3 and a.executable('/home/trainee/workspace/audit/report.sh') and a._r(r,'ls') and 'l' in r.meta.get('flags',set())))
        return L

    def current_lesson(self): return self.lessons[self.lesson_index] if self.lesson_index<len(self.lessons) else None
    def evaluate(self,res):
        cur=self.current_lesson()
        if not cur:return
        try: passed=cur.check(self,res)
        except Exception: passed=False
        if not passed:return
        cur.done=True; self.lesson_index+=1
        self._write(f'✓ Lesson complete: {cur.title}\n','success')
        if self.lesson_index>=len(self.lessons):
            self._write('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n','success'); self._write('LINUX TERMINAL LAB COMPLETE\n','success'); self._write('You completed the full progressive workstation workflow. The sandbox remains active, so you can keep experimenting with any supported command.\n','success'); self._write('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n','success')
        else:
            nxt=self.current_lesson(); self._write(f'Next → {nxt.title}\n\n','system')
        self.refresh_sidebar()

    def draw_progress(self):
        if not hasattr(self,'progress'):return
        self.progress.delete('all'); w=max(20,self.progress.winfo_width()); done=sum(x.done for x in self.lessons); pct=done/max(1,len(self.lessons)); self.progress.create_rectangle(0,0,w,9,fill='#16263C',outline='#16263C'); self.progress.create_rectangle(0,0,w*pct,9,fill=ACCENT,outline=ACCENT)

    def refresh_sidebar(self):
        done=sum(x.done for x in self.lessons); total=len(self.lessons); self.progress_text.configure(text=f'{done} / {total} lessons complete'); self.draw_progress()
        mode='REAL LINUX • CONTAINER' if self.shell.backend.available else 'PORTABLE • SANDBOX'; self.backend_chip.configure(text=f'{mode} • {BUILD_ID}')
        cur=self.current_lesson(); self.lesson_box.configure(state='normal'); self.lesson_box.delete('1.0','end')
        if cur:
            self.module_chip.configure(text=cur.module.upper()); self.lesson_title.configure(text=cur.title)
            self.lesson_box.insert('end','WHAT IT DOES\n','label'); self.lesson_box.insert('end',cur.why+'\n\n'); self.lesson_box.insert('end','TASK\n','label'); self.lesson_box.insert('end',cur.task+'\n\n'); self.lesson_box.insert('end','EXAMPLES\n','label')
            for ex in cur.examples:self.lesson_box.insert('end','  '+ex+'\n','example')
            self.lesson_box.see('1.0')
        else:self.module_chip.configure(text='COMPLETE'); self.lesson_title.configure(text='Training complete'); self.lesson_box.insert('end','Keep using the sandbox freely. Run `commands` to review built-ins.')
        self.lesson_box.configure(state='disabled')
        self.map_box.configure(state='normal'); self.map_box.delete('1.0','end'); lastmod=None; active_map_index=None
        for i,x in enumerate(self.lessons):
            if x.module!=lastmod:self.map_box.insert('end',('\n' if lastmod else '')+x.module+'\n','module');lastmod=x.module
            if i==self.lesson_index: active_map_index=self.map_box.index('end-1c')
            tag='done' if x.done else ('current' if i==self.lesson_index else None); symbol='✓' if x.done else ('▶' if i==self.lesson_index else '○'); self.map_box.insert('end',f' {symbol} {x.title}\n',tag)
        self.map_box.configure(state='disabled')
        if cur and active_map_index:self.after_idle(lambda idx=active_map_index:self._scroll_course_map(idx))

    def _scroll_course_map(self, idx):
        # Keep the active lesson visible. Lesson 1 always starts at the top.
        try:
            if self.lesson_index==0:self.map_box.yview_moveto(0.0)
            else:self.map_box.see(idx)
        except tk.TclError:pass

    def popup(self,title,message,width=610,height=360,mono=False):
        w=tk.Toplevel(self); w.title(title); w.configure(bg=BG); w.geometry(f'{width}x{height}'); w.transient(self)
        card=tk.Frame(w,bg=SURFACE,highlightthickness=1,highlightbackground=BORDER); card.pack(fill='both',expand=True,padx=14,pady=14)
        tk.Label(card,text=title,bg=SURFACE,fg=TEXT,font=('Segoe UI',15,'bold')).pack(anchor='w',padx=16,pady=(14,7))
        shell=tk.Frame(card,bg=SURFACE3,highlightthickness=1,highlightbackground=BORDER); shell.pack(fill='both',expand=True,padx=16,pady=(0,12)); shell.rowconfigure(0,weight=1); shell.columnconfigure(0,weight=1)
        box=tk.Text(shell,wrap='word',bg=SURFACE3,fg=SOFT,insertbackground=TEXT,relief='flat',bd=0,highlightthickness=0,font=(('Cascadia Mono',10) if mono else ('Segoe UI',11)),padx=12,pady=10); box.grid(row=0,column=0,sticky='nsew'); pop_sb=SeamlessScrollbar(shell,command=box.yview,track_color=SURFACE3,thumb_color='#294761',active_color='#3A6688',thickness=8); pop_sb.place(relx=1.0,rely=0.0,relheight=1.0,anchor='ne'); box.configure(yscrollcommand=pop_sb.set); box.insert('1.0',message); box.configure(state='disabled')
        ttk.Button(card,text='Close',style='Lab.TButton',command=w.destroy).pack(anchor='e',padx=16,pady=(0,14))
    def show_hint(self):
        cur=self.current_lesson(); self.popup('Hint',cur.hint if cur else 'All lessons are complete. Explore the sandbox freely.',height=260)
    def show_guide(self):
        extra=(f'\nExtra Linux commands: enabled through {self.shell.backend.runtime} / {self.shell.backend.image}. Unknown commands run inside the isolated, network-disabled container.\n' if self.shell.backend.available else '\nExtra Linux commands: container backend not detected. Portable mode still supports every lesson. See the README/Dockerfile to enable additional installed utilities.\n')
        msg='''COMMAND GUIDE\n\nNavigation       pwd  ls  cd  tree\nFiles            mkdir  rmdir  touch  cp  mv  rm  stat  file\nReading          cat  less  more  head  tail\nSearch           grep  find\nText             wc  sort  uniq  cut  tr  sed  awk  diff\nPermissions      chmod\nShell            echo  printf  tee  env  export  unset  history  alias  which  type\nSystem           whoami  id  hostname  uname  date  ps  df  du\nEditors          vi  vim  gvim  nano\nLearning         help  man <command>  commands\n\nOperators        |    >    >>    <    &&    ||    ;\n\nExamples\n  ls -ltr ~/projects\n  grep -ni error /var/log/training/app.log\n  find ~ -type f -name '*.conf'\n  grep ERROR /var/log/training/app.log | wc -l\n  sort /opt/training/data/owners.csv | uniq\n  chmod +x ~/scripts/report.sh\n  vim ~/workspace/onboarding/atlas.conf\n\nPortable mode: less/more print the file instead of opening a pager. vi/vim/gvim/nano open the lab editor. The optional container backend adds more installed Linux utilities and option forms.\n'''+extra
        self.popup('Linux Command Guide',msg,width=720,height=650,mono=True)

    def open_editor(self,vpath,editor_name):
        q=self.fs.real(vpath,self.shell.env); existing=q.exists()
        try:content=q.read_text(encoding='utf-8',errors='replace') if existing else ''
        except OSError as e:self._write(f'{editor_name}: {e}\n','error');return
        w=tk.Toplevel(self); w.title(f'{editor_name} • {vpath}'); w.configure(bg=BG); w.geometry('980x700'); w.minsize(720,500); w.transient(self)
        top=tk.Frame(w,bg=SURFACE2,height=58); top.pack(fill='x'); top.pack_propagate(False); tk.Label(top,text=f'{editor_name.upper()}  {vpath}',bg=SURFACE2,fg=TEXT,font=('Cascadia Mono',12,'bold')).pack(side='left',padx=16,pady=16); state=tk.Label(top,text='NORMAL • training sandbox',bg=SURFACE2,fg=ACCENT2,font=('Segoe UI',9,'bold')); state.pack(side='right',padx=16)
        edit_shell=tk.Frame(w,bg=TERM_BG,highlightthickness=1,highlightbackground='#14253A'); edit_shell.pack(fill='both',expand=True,padx=14,pady=(14,8)); edit_shell.rowconfigure(0,weight=1); edit_shell.columnconfigure(0,weight=1)
        area=tk.Text(edit_shell,undo=True,wrap='none',font=('Cascadia Mono',12),bg=TERM_BG,fg=TERM_FG,insertbackground=ACCENT2,selectbackground='#163558',relief='flat',bd=0,highlightthickness=0,padx=18,pady=18); area.grid(row=0,column=0,sticky='nsew'); editor_vsb=SeamlessScrollbar(edit_shell,command=area.yview,track_color=TERM_BG,thumb_color='#294761',active_color='#3A6688',thickness=8); editor_vsb.place(relx=1.0,rely=0.0,relheight=1.0,anchor='ne'); editor_hsb=SeamlessScrollbar(edit_shell,command=area.xview,orient='horizontal',track_color=TERM_BG,thumb_color='#294761',active_color='#3A6688',thickness=8); editor_hsb.place(relx=0.0,rely=1.0,relwidth=1.0,anchor='sw'); area.configure(yscrollcommand=editor_vsb.set,xscrollcommand=editor_hsb.set); area.insert('1.0',content); area.edit_modified(False); area.focus_set()
        bottom=tk.Frame(w,bg=BG); bottom.pack(fill='x',padx=14,pady=(0,14)); cmd=tk.Entry(bottom,font=('Cascadia Mono',11),bg=SURFACE3,fg=TEXT,insertbackground=TEXT,relief='flat',bd=0,highlightthickness=0,highlightbackground=SURFACE3,highlightcolor=SURFACE3); cmd.pack(side='left',fill='x',expand=True,ipady=8); tk.Label(bottom,text=' Ctrl+S save  •  :w save  •  :wq save & close  •  :q! discard ',bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='right',padx=(10,0))
        def save(close=False):
            try:q.parent.mkdir(parents=True,exist_ok=True);q.write_text(area.get('1.0','end-1c'),encoding='utf-8');area.edit_modified(False);state.configure(text='SAVED',fg=SUCCESS);self.evaluate(Result(editor_name,[vpath],f'{editor_name} {vpath}','',True,{'saved':vpath}));self.refresh_sidebar()
            except OSError as e:state.configure(text=f'SAVE ERROR: {e}',fg=ERROR);return
            if close:w.destroy();self.terminal.focus_set()
        def colon(e=None):
            x=cmd.get().strip();cmd.delete(0,'end')
            if x in (':w',':write'):save(False)
            elif x in (':wq',':x'):save(True)
            elif x==':q':
                if area.edit_modified():state.configure(text='UNSAVED CHANGES • use :wq to save or :q! to discard',fg=ERROR)
                else:w.destroy();self.terminal.focus_set()
            elif x==':q!':w.destroy();self.terminal.focus_set()
            else:state.configure(text=f'Unknown editor command: {x}',fg=ERROR)
        area.bind('<Control-s>',lambda e:(save(False),'break')[1]); cmd.bind('<Return>',colon); w.protocol('WM_DELETE_WINDOW',lambda:(w.destroy(),self.terminal.focus_set()))

    def reset_lab(self):
        # Any editor window is backed by the current temporary filesystem. Close
        # child windows first so an old editor cannot save into a discarded lab.
        for child in list(self.winfo_children()):
            if isinstance(child,tk.Toplevel):
                try:child.destroy()
                except tk.TclError:pass
        self.fs.cleanup(); self.fs=VirtualFS(); self.shell=Shell(self.fs,self.open_editor,self.clear_terminal); self.lessons=self.make_lessons(); self.lesson_index=0; self.history_index=None; self.clear_terminal(); self._welcome(); self._prompt(); self.refresh_sidebar()
    def close(self):
        self.fs.cleanup(); self.destroy()

if __name__=='__main__':
    LinuxTrainerApp().mainloop()
