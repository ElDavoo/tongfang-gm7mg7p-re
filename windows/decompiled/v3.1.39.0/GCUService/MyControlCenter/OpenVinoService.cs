using System;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;
using Utility;

namespace MyControlCenter;

internal class OpenVinoService : IDisposable
{
	public DataReceivedEventHandler OutputDataReceived;

	public DataReceivedEventHandler ErrorDataReceived;

	private string _Path_to_Script;

	private string _taskname = "human_pose_estimation_demo";

	private ProcessStartInfo startInfo;

	private Process process;

	private bool _HasProcess;

	private static readonly OpenVinoService _OpenVinoService = new OpenVinoService();

	public static OpenVinoService Instance => _OpenVinoService;

	public void Init(string Path_to_Script)
	{
		_Path_to_Script = Path_to_Script;
		startInfo = new ProcessStartInfo();
		process = new Process();
		InitBashInfo();
	}

	private void InitBashInfo()
	{
		startInfo.FileName = _Path_to_Script;
		startInfo.UseShellExecute = false;
		startInfo.RedirectStandardOutput = true;
		startInfo.RedirectStandardError = true;
		process.StartInfo = startInfo;
		process.StartInfo.CreateNoWindow = true;
		process.OutputDataReceived += Process_OutputDataReceived;
		process.ErrorDataReceived += Process_ErrorDataReceived;
	}

	private void Process_ErrorDataReceived(object sender, DataReceivedEventArgs e)
	{
		LogCtrl.Write("Face Detection !" + e.Data);
		if (ErrorDataReceived != null)
		{
			ErrorDataReceived(sender, e);
		}
	}

	private void Process_OutputDataReceived(object sender, DataReceivedEventArgs e)
	{
		try
		{
			string[] array = e.Data.ToString().Split(' ');
			if (array.Count() > 0 && array[0].ToString().Contains(".exe"))
			{
				_taskname = array[0];
			}
			if (OutputDataReceived != null)
			{
				OutputDataReceived(sender, e);
			}
		}
		catch (Exception)
		{
		}
	}

	public void Start()
	{
		_HasProcess = true;
		Task.Run(delegate
		{
			try
			{
				process.Start();
				process.BeginOutputReadLine();
				process.WaitForExit();
			}
			catch (Exception)
			{
				Dispose();
			}
		});
	}

	internal bool HasProcess()
	{
		return _HasProcess;
	}

	public void Stop()
	{
		Dispose();
	}

	private void EndCPlusFromProcess()
	{
		Process[] processesByName = Process.GetProcessesByName(_taskname.Replace(".exe", ""));
		for (int i = 0; i < processesByName.Length; i++)
		{
			processesByName[i].Kill();
		}
	}

	public void Dispose()
	{
		OutputDataReceived = null;
		ErrorDataReceived = null;
		startInfo = null;
		if (process != null)
		{
			try
			{
				EndCPlusFromProcess();
				process.CloseMainWindow();
				process.CancelOutputRead();
				process.Close();
				process.Dispose();
				process.Kill();
			}
			catch (Exception)
			{
			}
		}
		_HasProcess = false;
	}

	void IDisposable.Dispose()
	{
		//ILSpy generated this explicit interface implementation from .override directive in Dispose
		this.Dispose();
	}
}
