from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path
from conversation_exports import extract_conversations,ConversationExportError
from folder_watch import FolderWatcher
from google_drive_ingest import GoogleDriveIngestor

class LifeContextPipeline:
    """Connectors feed exact local files into the existing canonical Context Library."""
    def __init__(self,core,settings,inbox_root):
        self.core=core;self.settings=settings;self.root=Path(inbox_root).expanduser().resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.folder=None;self.drive=None
        roots=[os.path.expandvars(os.path.expanduser(str(x))) for x in settings.get('watch_folders',[]) if str(x).strip()]
        if roots:self.folder=FolderWatcher(roots,self.root/'folder-watch-v7.json')
        drive=settings.get('google_drive') or {}
        if drive.get('enabled') is True:self.drive=GoogleDriveIngestor(drive,self.root/'google-drive-state.json')
    def _capture(self,path,source_key,project,note,labels=None):
        receipt=self.core.capture_file(path,source_key)
        try:self.core.annotate_capture(receipt,project=project,note=note,labels=labels or [])
        except Exception:pass
        return receipt
    def poll_once(self,emit_existing_drive=False):
        results=[]
        if self.folder:
            for row in self.folder.scan():
                key='life_'+row['sha256'][:20]
                try:
                    receipt=self._capture(row['path'],key,'LifeContext','local-file '+Path(row['path']).name,labels=['source:local-file','type:'+((Path(row['path']).suffix.lower().lstrip('.') or 'file'))])
                    results.append({'source':'folder','state':'CAPTURED','file':row,'receipt':receipt})
                    if Path(row['path']).suffix.lower() in {'.json','.jsonl'}:
                        try:
                            derived=extract_conversations(row['path'],self.root/'derived-conversations')
                            for conv in derived:
                                ckey='conversation_'+conv['sha256'][:20]
                                creceipt=self._capture(conv['path'],ckey,'Conversations','derived from '+str(conv['source_export'])+' id='+str(conv['conversation_id']),labels=['source:conversation-export','type:conversation'])
                                results.append({'source':'conversation_export','state':'CAPTURED','conversation':conv,'receipt':creceipt})
                        except ConversationExportError:
                            pass
                except Exception as exc:results.append({'source':'folder','state':'BLOCKED','file':row,'reason':str(exc)})
        if self.drive:
            for row in self.drive.poll(emit_existing=emit_existing_drive):
                if row.get('state')!='DOWNLOADED':results.append({'source':'google_drive',**row});continue
                key='gdrive_'+row['file_id'][:24].replace('-','_')
                note='Google Drive file_id='+row['file_id']+' mime='+str(row.get('mime_type'))+' modified='+str(row.get('modified_time'))
                try:
                    receipt=self._capture(row['path'],key,'GoogleDrive',note,labels=['source:google-drive','type:document','mime:'+str(row.get('mime_type') or 'unknown')[:70]])
                    results.append({'source':'google_drive','state':'CAPTURED','file':row,'receipt':receipt})
                except Exception as exc:results.append({'source':'google_drive','state':'BLOCKED','file':row,'reason':str(exc)})
        return {'schema':'voice-agentos.life-context-poll.v1','checked_at':time.time(),'results':results}
