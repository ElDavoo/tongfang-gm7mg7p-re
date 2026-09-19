using System.Collections.Generic;
using Define;

namespace Utility;

public static class ProjectIdExtensions
{
	private static List<ProjectID> CommercialProjectIDs = new List<ProjectID>
	{
		ProjectID.PF,
		ProjectID.PF4MU_PF4MN_PF5MU,
		ProjectID.GM5MU1Y,
		ProjectID.PH4TRX1,
		ProjectID.PH4TUX1,
		ProjectID.PH4TQx1,
		ProjectID.PH6TRX1
	};

	private static List<ProjectID> SingleColorKeyboardProjectIDs = new List<ProjectID>
	{
		ProjectID.PF,
		ProjectID.PF4MU_PF4MN_PF5MU,
		ProjectID.PH4TRX1,
		ProjectID.PH4TUX1,
		ProjectID.PH4TQx1,
		ProjectID.PH6TRX1,
		ProjectID.PH6TQxx
	};

	private static List<ProjectID> NonNumPadProjectIDs = new List<ProjectID>
	{
		ProjectID.PH4TRX1,
		ProjectID.PH4TUX1,
		ProjectID.PH4TQx1
	};

	private static List<ProjectID> IDYIDPProjectIDs = new List<ProjectID>
	{
		ProjectID.IDP,
		ProjectID.IDY_6Y,
		ProjectID.IDY_7Y
	};

	public static bool IsProjectId_Commercial(this int ProjId)
	{
		return CommercialProjectIDs.Contains((ProjectID)ProjId);
	}

	public static bool IsProjectId_SingleColorKeyboard(this int ProjId)
	{
		return SingleColorKeyboardProjectIDs.Contains((ProjectID)ProjId);
	}

	public static bool IsProjectId_NonNumPad(this int ProjId)
	{
		return NonNumPadProjectIDs.Contains((ProjectID)ProjId);
	}

	public static bool IsProjectId_IDPIDY(this int ProjId)
	{
		return IDYIDPProjectIDs.Contains((ProjectID)ProjId);
	}

	public static bool IsProjectId_NoRgblbSupport(this int ProjId)
	{
		if (ProjId <= 3 || ProjId.IsProjectId_Commercial())
		{
			return true;
		}
		return false;
	}
}
