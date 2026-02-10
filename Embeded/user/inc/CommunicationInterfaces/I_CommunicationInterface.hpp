/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __I_COMMUNICATION_INTERFACE_HPP
#define __I_COMMUNICATION_INTERFACE_HPP

/* Includes ------------------------------------------------------------------*/
#include "BasePackage.hpp"

/* Defines -------------------------------------------------------------------*/

// -----------------------------------------------------------------------------
// Class comment
class I_CommunicationInterface{
    virtual void Init() = 0;
    virtual void SendPackage(BasePackage& package) = 0;
};

#endif /*   __I_COMMUNICATION_INTERFACE_HPP   */