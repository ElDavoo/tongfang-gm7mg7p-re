using System;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using Utility;

namespace MyControlCenter.MyFan.FanTable;

public static class LocalFileLoader
{
	private static string m_path = new FileInfo(Assembly.GetExecutingAssembly().Location).DirectoryName;

	public static T LoadJsonFromPath_NonAsync<T>(string filenpath, string filename, Assembly assembly)
	{
		string path = filenpath + "\\" + filename + ".json";
		if (File.Exists(path))
		{
			return Json.ToObject<T>(File.ReadAllText(path));
		}
		return default(T);
	}

	public static async Task<T> LoadJsonFromPath<T>(string _filename, Assembly assembly)
	{
		string path = m_path + "\\FanTable\\User\\" + _filename + ".json";
		if (File.Exists(path))
		{
			return await Json.ToObjectAsync<T>(File.ReadAllText(path));
		}
		return default(T);
	}

	public static void CopyFileFromPath(string _fileName)
	{
		try
		{
			string text = m_path + "\\FanTable\\Default";
			string text2 = m_path + "\\FanTable\\User";
			string sourceFileName = text + "\\" + _fileName + ".json";
			string destFileName = text2 + "\\" + _fileName + ".json";
			if (!Directory.Exists(text2))
			{
				Directory.CreateDirectory(text2);
			}
			File.Copy(sourceFileName, destFileName, overwrite: true);
		}
		catch
		{
		}
	}

	public static void CopyFolderFromPath(string _sourceDir, string _targetDir)
	{
		try
		{
			string path = m_path + "\\FanTable\\" + _sourceDir;
			string text = m_path + "\\FanTable\\" + _targetDir;
			if (Directory.Exists(path))
			{
				string[] files = Directory.GetFiles(path);
				if (!Directory.Exists(text))
				{
					Directory.CreateDirectory(text);
				}
				string[] array = files;
				foreach (string obj in array)
				{
					string fileName = Path.GetFileName(obj);
					string destFileName = Path.Combine(text, fileName);
					File.Copy(obj, destFileName, overwrite: true);
				}
			}
			else
			{
				Console.WriteLine("Source path does not exist!");
			}
		}
		catch
		{
		}
	}

	public static bool CheckFile(string _fileName)
	{
		bool result = false;
		try
		{
			if (File.Exists(m_path + "\\FanTable\\User\\" + _fileName + ".json"))
			{
				result = true;
			}
		}
		catch
		{
			result = false;
		}
		return result;
	}

	public static bool DeleteFolder(string _folderName)
	{
		bool result = false;
		try
		{
			string path = m_path + "\\FanTable\\" + _folderName;
			if (Directory.Exists(path))
			{
				Directory.Delete(path, recursive: true);
				result = (Directory.Exists(path) ? true : false);
			}
		}
		catch (Exception)
		{
		}
		return result;
	}
}
