using System.Collections.Generic;
using Microsoft.Win32;

namespace GCUService.MySystem;

internal class ForceToGPU
{
	private const string GPURegistryString = "Software\\Microsoft\\DirectX\\UserGpuPreferences";

	private Dictionary<string, string> ProcessPathMap = new Dictionary<string, string>();

	public void AddProcess(string ProcessPath, int value)
	{
		Registry.SetValue("HKEY_CURRENT_USER\\Software\\Microsoft\\DirectX\\UserGpuPreferences", ProcessPath, "GpuPreference=" + value + ";");
	}

	public void SetProcessMapping(string name, string path)
	{
		if (!ProcessPathMap.ContainsKey(name))
		{
			ProcessPathMap.Add(name, path);
		}
		else
		{
			ProcessPathMap[name] = path;
		}
	}

	public void DelProcess(string ProcessName)
	{
		if (ProcessPathMap.ContainsKey(ProcessName))
		{
			Registry.CurrentUser.DeleteSubKey("Software\\Microsoft\\DirectX\\UserGpuPreferences\\" + ProcessPathMap[ProcessName]);
			string key = ProcessPathMap[ProcessName];
			ProcessPathMap.Remove(key);
		}
	}
}
