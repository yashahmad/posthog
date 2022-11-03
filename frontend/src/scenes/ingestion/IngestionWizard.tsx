import { useEffect } from 'react'
import './IngestionWizard.scss'

import { VerificationPanel } from 'scenes/ingestion/panels/VerificationPanel'
import { InstructionsPanel } from 'scenes/ingestion/panels/InstructionsPanel'
import { MOBILE, BACKEND, WEB, BOOKMARKLET, THIRD_PARTY } from 'scenes/ingestion/constants'
import { useValues, useActions } from 'kea'
import { ingestionLogic } from 'scenes/ingestion/ingestionLogic'
import { FrameworkPanel } from 'scenes/ingestion/panels/FrameworkPanel'
import { PlatformPanel } from 'scenes/ingestion/panels/PlatformPanel'
import { eventUsageLogic } from 'lib/utils/eventUsageLogic'
import { SceneExport } from 'scenes/sceneTypes'
import { BookmarkletPanel } from './panels/BookmarkletPanel'
import { ThirdPartyPanel } from './panels/ThirdPartyPanel'
import { BillingPanel } from './panels/BillingPanel'
import { Sidebar } from './Sidebar'
import { InviteModal } from 'scenes/organization/Settings/InviteModal'
import { inviteLogic } from 'scenes/organization/Settings/inviteLogic'
import { FriendlyLogo } from '~/toolbar/assets/FriendlyLogo'
import { SitePopover } from '~/layout/navigation/TopBar/SitePopover'
import { HelpButton } from 'lib/components/HelpButton/HelpButton'
import { BridgePage } from 'lib/components/BridgePage/BridgePage'
import { PanelHeader } from './panels/PanelComponents'
import { InviteTeamPanel } from './panels/InviteTeamPanel'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { FEATURE_FLAGS } from 'lib/constants'

export const scene: SceneExport = {
    component: IngestionWizard,
    logic: ingestionLogic,
}

export function IngestionWizard(): JSX.Element {
    const { platform, framework, verify, addBilling, technical } = useValues(ingestionLogic)
    const { reportIngestionLandingSeen } = useActions(eventUsageLogic)
    const { featureFlags } = useValues(featureFlagLogic)

    useEffect(() => {
        if (!platform) {
            reportIngestionLandingSeen()
        }
    }, [platform])

    if (addBilling) {
        return (
            <IngestionContainer>
                <BillingPanel />
            </IngestionContainer>
        )
    }

    if (!platform && !verify && !!featureFlags[FEATURE_FLAGS.ONBOARDING_V2] && !technical) {
        return (
            <IngestionContainer>
                <InviteTeamPanel />
            </IngestionContainer>
        )
    }

    if (!platform && !verify && !!featureFlags[FEATURE_FLAGS.ONBOARDING_V2] ? technical : true) {
        return (
            <IngestionContainer>
                <PlatformPanel />
            </IngestionContainer>
        )
    }

    if (verify) {
        return (
            <IngestionContainer>
                <VerificationPanel />
            </IngestionContainer>
        )
    }

    if (framework || platform === WEB) {
        return (
            <IngestionContainer>
                <InstructionsPanel />
            </IngestionContainer>
        )
    }

    if (platform === MOBILE || platform === BACKEND) {
        return (
            <IngestionContainer>
                <FrameworkPanel />
            </IngestionContainer>
        )
    }

    if (platform === BOOKMARKLET) {
        return (
            <IngestionContainer>
                <BookmarkletPanel />
            </IngestionContainer>
        )
    }

    if (platform === THIRD_PARTY) {
        return (
            <IngestionContainer>
                <ThirdPartyPanel />
            </IngestionContainer>
        )
    }

    return <></>
}

function IngestionContainer({ children }: { children: React.ReactNode }): JSX.Element {
    const { isInviteModalShown } = useValues(inviteLogic)
    const { hideInviteModal } = useActions(inviteLogic)
    const { isSmallScreen } = useValues(ingestionLogic)

    return (
        <div className="flex h-full flex-col">
            <div className="IngestionTopbar">
                <FriendlyLogo style={{ fontSize: '1.125rem' }} />
                <div className="flex">
                    <HelpButton />
                    <SitePopover />
                </div>
            </div>
            <InviteModal isOpen={isInviteModalShown} onClose={hideInviteModal} />
            <div className="flex h-full">
                {!isSmallScreen && <Sidebar />}
                {/* <div className="IngestionContainer" */}
                <BridgePage view="ingestion" noHedgehog noLogo fixedWidth={false} header={<PanelHeader />}>
                    {children}
                </BridgePage>
            </div>
        </div>
    )
}
