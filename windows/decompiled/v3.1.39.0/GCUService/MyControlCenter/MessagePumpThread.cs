using System;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Utility;

namespace MyControlCenter;

internal sealed class MessagePumpThread : IDisposable
{
	private Thread thread;

	private readonly TaskCompletionSource<Exception> initResult = new TaskCompletionSource<Exception>();

	private ApplicationContext applicationContext;

	private bool disposed;

	public void Start(Action init)
	{
		thread = new Thread((ThreadStart)delegate
		{
			try
			{
				using (applicationContext = new ApplicationContext())
				{
					init();
				}
			}
			catch (Exception ex)
			{
				if (!initResult.TrySetResult(ex))
				{
					LogCtrl.Write("Exception in dedicated message pump thread. Exception: " + ex);
				}
			}
		});
		thread.SetApartmentState(ApartmentState.STA);
		thread.Start();
		if (initResult.Task.Result != null)
		{
			throw initResult.Task.Result;
		}
	}

	public void EnterMessageLoop()
	{
		initResult.SetResult(null);
		Application.Run(applicationContext);
	}

	public void Dispose()
	{
		if (!disposed)
		{
			disposed = true;
			if (applicationContext != null)
			{
				applicationContext.ExitThread();
				thread.Join(TimeSpan.Zero);
				applicationContext.Dispose();
			}
		}
	}

	void IDisposable.Dispose()
	{
		//ILSpy generated this explicit interface implementation from .override directive in Dispose
		this.Dispose();
	}
}
