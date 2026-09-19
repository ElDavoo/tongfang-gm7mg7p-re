using System;
using System.Threading;

namespace Utility;

internal class WriteLock : IDisposable
{
	private ReaderWriterLockSlim _rwLock;

	public WriteLock(ReaderWriterLockSlim rwLock)
	{
		_rwLock = rwLock;
		try
		{
			_rwLock.EnterWriteLock();
		}
		finally
		{
			_rwLock.ExitWriteLock();
		}
	}

	public void Dispose()
	{
		if (_rwLock.IsWriteLockHeld)
		{
			_rwLock.ExitWriteLock();
		}
	}

	void IDisposable.Dispose()
	{
		//ILSpy generated this explicit interface implementation from .override directive in Dispose
		this.Dispose();
	}
}
