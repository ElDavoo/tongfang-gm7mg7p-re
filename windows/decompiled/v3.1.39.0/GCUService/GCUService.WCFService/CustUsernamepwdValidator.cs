using System;
using System.IdentityModel.Selectors;

namespace GCUService.WCFService;

public class CustUsernamepwdValidator : UserNamePasswordValidator
{
	public override void Validate(string userName, string password)
	{
		if (userName != "admin" || password != "321")
		{
			throw new Exception("user or password error");
		}
	}
}
