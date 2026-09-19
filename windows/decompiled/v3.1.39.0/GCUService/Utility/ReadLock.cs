using System;
using System.Threading;

namespace Utility;

internal class ReadLock : IDisposable
{
	private ReaderWriterLockSlim _rwLock;

	public ReadLock(ReaderWriterLockSlim rwLock)
	{
		_rwLock = rwLock;
		try
		{
			_rwLock.EnterReadLock();
		}
		finally
		{
			_rwLock.ExitReadLock();
		}
	}

	public void Dispose()
	{
		if (_rwLock.IsReadLockHeld)
		{
			_rwLock.ExitReadLock();
		}
	}

	void IDisposable.Dispose()
	{
		//ILSpy generated this explicit interface implementation from .override directive in Dispose
		this.Dispose();
	}
}
