using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Win32;
using MyControlCenter.MyFan;

namespace Utility;

internal class LogCtrl
{
	public enum LogFileCreateMode
	{
		FollowRegistry,
		Keep,
		CreateNew
	}

	private static bool b_LogEnable = false;

	private static string m_LogPath = "C:\\MyControlCenter.log";

	private static object queuelock = new object();

	private static object myWriteLock = new object();

	private static Queue<string> MsgQueue = new Queue<string>();

	private static BackgroundQueue backgroundQueue = new BackgroundQueue();

	private static ReaderWriterLockSlim _lock = new ReaderWriterLockSlim();

	private static string indent_token = "  ";

	private static int indent_count = 0;

	public static bool WithAssemblyName = false;

	private static readonly string AssemblyName = Path.GetFileNameWithoutExtension(Assembly.GetExecutingAssembly().ManifestModule.Name);

	public static void SetLogPath(string logpath)
	{
		m_LogPath = logpath;
	}

	public static void EnableLog(LogFileCreateMode create_mode = LogFileCreateMode.FollowRegistry)
	{
		try
		{
			object obj = RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenterService\\Debug", "enable", 0);
			if (obj != null)
			{
				b_LogEnable = (int)obj > 0;
			}
		}
		catch
		{
			b_LogEnable = false;
			return;
		}
		switch (create_mode)
		{
		case LogFileCreateMode.CreateNew:
			File.Delete(m_LogPath);
			break;
		case LogFileCreateMode.FollowRegistry:
			try
			{
				object obj3 = RegistryCtrl.RegistrySoftwareKeyRead(RegistryHive.LocalMachine, "\\OEM\\GamingCenterService\\Debug", "create", 0);
				if (obj3 != null && (int)obj3 > 0)
				{
					File.Delete(m_LogPath);
				}
				break;
			}
			catch
			{
				break;
			}
		case LogFileCreateMode.Keep:
			break;
		}
	}

	public static void DisableLog()
	{
		b_LogEnable = false;
	}

	public static void Write(string logMessage)
	{
		Task.Run(delegate
		{
			if (WithAssemblyName)
			{
				logMessage = AssemblyName + " | " + logMessage;
			}
			if (b_LogEnable && Monitor.TryEnter(myWriteLock, 2000))
			{
				try
				{
					using FileStream stream = new FileStream(m_LogPath, FileMode.Append);
					using StreamWriter streamWriter = new StreamWriter(stream);
					streamWriter.WriteLine("{0} - {1} ", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"), logMessage);
				}
				catch (Exception)
				{
					backgroundQueue.QueueTask(delegate
					{
						Write(logMessage);
					});
				}
				finally
				{
					Monitor.Exit(myWriteLock);
				}
			}
		});
	}

	public static void Write_test(string logMessage)
	{
		bool lockTaken = false;
		if (WithAssemblyName)
		{
			logMessage = AssemblyName + " | " + logMessage;
		}
		try
		{
			if (b_LogEnable)
			{
				Monitor.TryEnter(myWriteLock, ref lockTaken);
				if (!lockTaken)
				{
					return;
				}
				using StreamWriter streamWriter = File.AppendText(m_LogPath);
				Queue<string> msgQueue = MsgQueue;
				if (msgQueue != null && msgQueue.Count <= 0)
				{
					streamWriter.WriteLine("{0}", logMessage);
					return;
				}
				MsgQueue?.Enqueue(logMessage);
				while (true)
				{
					Queue<string> msgQueue2 = MsgQueue;
					if (msgQueue2 != null && msgQueue2.Count > 0)
					{
						string arg = MsgQueue?.Dequeue();
						streamWriter.WriteLine("{0}", arg);
						continue;
					}
					break;
				}
				return;
			}
			Console.WriteLine(logMessage);
		}
		catch (Exception)
		{
		}
		finally
		{
			if (lockTaken)
			{
				Monitor.Exit(myWriteLock);
			}
			else
			{
				lock (queuelock)
				{
					if (MsgQueue != null)
					{
						MsgQueue?.Enqueue(logMessage);
					}
				}
			}
		}
	}

	public static string GetTime()
	{
		DateTime dateTime = default(DateTime);
		return DateTime.Now.ToString("yyyy-MM-dd_hh-mm-ss_fff");
	}

	public static string GetParentDirectoryPath(string folderPath, int levels)
	{
		string text = folderPath;
		for (int i = 0; i < levels; i++)
		{
			if (Directory.GetParent(text) != null)
			{
				text = Directory.GetParent(text).FullName;
				continue;
			}
			return text;
		}
		return text;
	}

	public static string GetParentDirectoryPath(string folderPath)
	{
		return GetParentDirectoryPath(folderPath, 1);
	}

	public static void Indent()
	{
		indent_count++;
	}

	public static void Unindent()
	{
		indent_count--;
		if (indent_count < 0)
		{
			indent_count = 0;
		}
	}

	public static void TraceMessage(string message = "", [CallerMemberName] string memberName = "", [CallerFilePath] string sourceFilePath = "", [CallerLineNumber] int sourceLineNumber = 0)
	{
		if (b_LogEnable)
		{
			string text = string.Concat(Enumerable.Repeat(indent_token, indent_count));
			string name = new StackFrame(1).GetMethod().ReflectedType.Name;
			if (name.StartsWith("<"))
			{
				name = new StackFrame(1).GetMethod().DeclaringType.ReflectedType.Name;
			}
			if (memberName == ".ctor")
			{
				memberName = name;
			}
			string logMessage = ((!WithAssemblyName) ? (text + name + " | " + memberName + " | " + message) : (text + "[" + AssemblyName + "] [" + name + "] [" + memberName + "] " + message));
			Write(logMessage);
		}
	}

	[Conditional("DEBUG")]
	public static void TraceMessage(string format, params object[] args)
	{
		if (b_LogEnable)
		{
			string text = string.Format(CultureInfo.InvariantCulture, format, args);
			string text2 = string.Concat(Enumerable.Repeat(indent_token, indent_count));
			string name = new StackFrame(1).GetMethod().ReflectedType.Name;
			string text3 = new StackFrame(1, fNeedFileInfo: false).GetMethod().Name;
			if (name.StartsWith("<"))
			{
				name = new StackFrame(1).GetMethod().DeclaringType.ReflectedType.Name;
			}
			if (text3 == ".ctor")
			{
				text3 = name;
			}
			string logMessage = ((!WithAssemblyName) ? (text2 + name + " | " + text3 + " | " + text) : (text2 + "[" + AssemblyName + "] [" + name + "] [" + text3 + "] " + text));
			Write(logMessage);
		}
	}
}
