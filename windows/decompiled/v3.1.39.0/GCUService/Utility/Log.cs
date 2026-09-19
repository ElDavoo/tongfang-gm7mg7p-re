using System;
using System.IO;
using System.Reflection;

namespace Utility;

public static class Log
{
	private static bool m_bEnable = false;

	private static string m_logName = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName + "\\RGBKeyboard.log";

	public static void s(LOG_LEVEL log_level, string strLog)
	{
		string value = "[" + log_level.ToString() + "]" + strLog;
		if (m_bEnable)
		{
			using (StreamWriter streamWriter = File.AppendText(m_logName))
			{
				streamWriter.WriteLine(value);
				return;
			}
		}
		Console.WriteLine(value);
	}

	public static void EnableLog(bool enable)
	{
		m_bEnable = enable;
	}
}
