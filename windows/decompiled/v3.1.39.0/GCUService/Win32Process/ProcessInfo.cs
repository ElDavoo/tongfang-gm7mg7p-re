using System;
using System.Data;
using System.Management;
using Utility;

namespace Win32Process;

public class ProcessInfo
{
	public delegate void StartedEventHandler(object sender, EventArgs e);

	public delegate void TerminatedEventHandler(object sender, EventArgs e);

	public string _appName;

	public StartedEventHandler Started;

	public TerminatedEventHandler Terminated;

	private ManagementEventWatcher watcher;

	public ProcessInfo(string appName)
	{
		try
		{
			_appName = appName;
			string text = "2";
			string query = "SELECT *  FROM __InstanceOperationEvent WITHIN  " + text + " WHERE TargetInstance ISA 'Win32_Process'    AND TargetInstance.Name = '" + appName + "'";
			string scope = "\\\\.\\root\\CIMV2";
			watcher = new ManagementEventWatcher(scope, query);
			watcher.EventArrived += OnEventArrived;
			watcher.Start();
		}
		catch (Exception)
		{
			LogCtrl.Write("ProcessControl init error");
		}
	}

	public void Dispose()
	{
		watcher.Stop();
		watcher.Dispose();
	}

	public static DataTable RunningProcesses()
	{
		SelectQuery query = new SelectQuery("SELECT Name, ProcessId, Caption, ExecutablePath  FROM Win32_Process");
		ManagementObjectCollection managementObjectCollection = new ManagementObjectSearcher(new ManagementScope("\\\\.\\root\\CIMV2"), query).Get();
		DataTable dataTable = new DataTable
		{
			Columns = 
			{
				{
					"Name",
					Type.GetType("System.String")
				},
				{
					"ProcessId",
					Type.GetType("System.Int32")
				},
				{
					"Caption",
					Type.GetType("System.String")
				},
				{
					"Path",
					Type.GetType("System.String")
				}
			}
		};
		foreach (ManagementObject item in managementObjectCollection)
		{
			DataRow dataRow = dataTable.NewRow();
			dataRow["Name"] = item["Name"].ToString();
			dataRow["ProcessId"] = Convert.ToInt32(item["ProcessId"]);
			if (item["Caption"] != null)
			{
				dataRow["Caption"] = item["Caption"].ToString();
			}
			if (item["ExecutablePath"] != null)
			{
				dataRow["Path"] = item["ExecutablePath"].ToString();
			}
			dataTable.Rows.Add(dataRow);
		}
		return dataTable;
	}

	private void OnEventArrived(object sender, EventArrivedEventArgs e)
	{
		try
		{
			string className = e.NewEvent.ClassPath.ClassName;
			if (className.CompareTo("__InstanceCreationEvent") == 0)
			{
				if (Started != null)
				{
					Started(this, e);
				}
			}
			else if (className.CompareTo("__InstanceDeletionEvent") == 0 && Terminated != null)
			{
				Terminated(this, e);
			}
		}
		catch (Exception)
		{
		}
	}
}
