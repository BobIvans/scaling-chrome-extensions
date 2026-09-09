using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using System.Collections.Generic;
class NativeHost {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr attributes,string name);
 [DllImport("kernel32.dll")] static extern bool SetInformationJobObject(IntPtr job,int infoClass,IntPtr info,uint length);
 [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 [StructLayout(LayoutKind.Sequential)] struct BasicLimits {public long PerProcessUserTimeLimit,PerJobUserTimeLimit;public uint LimitFlags;public UIntPtr MinimumWorkingSetSize,MaximumWorkingSetSize;public uint ActiveProcessLimit;public UIntPtr Affinity;public uint PriorityClass,SchedulingClass;}
 [StructLayout(LayoutKind.Sequential)] struct IoCounters {public ulong ReadOperationCount,WriteOperationCount,OtherOperationCount,ReadTransferCount,WriteTransferCount,OtherTransferCount;}
 [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits {public BasicLimits BasicLimitInformation;public IoCounters IoInfo;public UIntPtr ProcessMemoryLimit,JobMemoryLimit,PeakProcessMemoryUsed,PeakJobMemoryUsed;}
 static string Quote(string value){return "\""+value.Replace("\"","\\\"")+"\"";}
 static void Pump(Stream source,Stream destination){var buffer=new byte[8192];int count;while((count=source.Read(buffer,0,buffer.Length))>0){destination.Write(buffer,0,count);destination.Flush();}}
 static int Main(string[] args){
  IntPtr job=IntPtr.Zero;Process child=null;
  try{
   string root=AppDomain.CurrentDomain.BaseDirectory;
   var config=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(root,"host-config.json")));
   string origin="chrome-extension://"+(string)config["extensionId"]+"/";
   if(args.Length<1||args[0]!=origin)return 2;
   job=CreateJobObject(IntPtr.Zero,null);if(job==IntPtr.Zero)return 3;
   var limits=new ExtendedLimits();limits.BasicLimitInformation.LimitFlags=0x2000; // kill descendants on host exit
   int size=Marshal.SizeOf(limits);IntPtr memory=Marshal.AllocHGlobal(size);
   try{Marshal.StructureToPtr(limits,memory,false);if(!SetInformationJobObject(job,9,memory,(uint)size))return 3;}finally{Marshal.FreeHGlobal(memory);}
   child=new Process();child.StartInfo=new ProcessStartInfo((string)config["nodePath"],Quote(Path.Combine(root,"host.mjs"))+" "+Quote(origin)){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=root,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true};
   child.Start();if(!AssignProcessToJobObject(job,child.Handle)){child.Kill();return 3;}
   var input=new Thread(()=>{try{Pump(Console.OpenStandardInput(),child.StandardInput.BaseStream);child.StandardInput.Close();}catch{}});input.IsBackground=true;input.Start();
   var errors=new Thread(()=>{try{child.StandardError.ReadToEnd();}catch{}});errors.IsBackground=true;errors.Start();
   Pump(child.StandardOutput.BaseStream,Console.OpenStandardOutput());child.WaitForExit();return child.ExitCode;
  }catch{return 2;}
  finally{if(job!=IntPtr.Zero)CloseHandle(job);if(child!=null)child.Dispose();}
 }
}
