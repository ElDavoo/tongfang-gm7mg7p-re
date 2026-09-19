using System;
using System.Threading;
using System.Threading.Tasks;

namespace MyControlCenter.MyFan;

public class BackgroundQueue
{
	private Task previousTask = Task.FromResult(result: true);

	private object key = new object();

	private CancellationTokenSource cts = new CancellationTokenSource();

	public void forceAbort()
	{
		cts.Cancel();
		cts.Dispose();
	}

	public Task QueueTask(Action action)
	{
		lock (key)
		{
			CancellationToken token = cts.Token;
			previousTask = previousTask.ContinueWith(delegate
			{
				action();
			}, token, TaskContinuationOptions.None, TaskScheduler.Default);
			return previousTask;
		}
	}

	public Task<T> QueueTask<T>(Func<T> work)
	{
		lock (key)
		{
			return (Task<T>)(previousTask = previousTask.ContinueWith((Task t) => work(), CancellationToken.None, TaskContinuationOptions.None, TaskScheduler.Default));
		}
	}
}
