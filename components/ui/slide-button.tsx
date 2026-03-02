"use client"

import React, {
    forwardRef,
    useCallback,
    useMemo,
    useRef,
    useState,
    type JSX,
} from "react"
import {
    AnimatePresence,
    motion,
    useMotionValue,
    useSpring,
    useTransform,
    type PanInfo,
} from "framer-motion"
import { Check, Loader2, ArrowRight, X } from "lucide-react"

import { cn } from "@/lib/utils"
// Ensure we use our Button
import { Button, ButtonProps } from "@/components/ui/button"

const DRAG_CONSTRAINTS = { left: 0, right: 155 }
const DRAG_THRESHOLD = 0.9

const BUTTON_STATES = {
    initial: { width: "12rem" },
    completed: { width: "8rem" },
}

const ANIMATION_CONFIG = {
    spring: {
        type: "spring" as const,
        stiffness: 400,
        damping: 40,
        mass: 0.8,
    },
}

type StatusIconProps = {
    status: string
}

const StatusIcon: React.FC<StatusIconProps> = ({ status }) => {
    const iconMap: Record<StatusIconProps["status"], JSX.Element> = useMemo(
        () => ({
            loading: <Loader2 className="animate-spin text-[#A0522D]" size={20} />,
            success: <Check className="text-[#A0522D]" size={20} />,
            error: <X className="text-[#E35336]" size={20} />,
        }),
        []
    )

    if (!iconMap[status]) return null

    return (
        <motion.div
            key={Math.random().toString(36).slice(2)}
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
        >
            {iconMap[status]}
        </motion.div>
    )
}

export interface SlideButtonProps extends ButtonProps {
    onSuccess?: () => void;
    resetOnSuccess?: boolean;
}

export const SlideButton = forwardRef<HTMLButtonElement, SlideButtonProps>(
    ({ className, onSuccess, resetOnSuccess, disabled, children, ...props }, ref) => {
        const [isDragging, setIsDragging] = useState(false)
        const [completed, setCompleted] = useState(false)
        const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
        const dragHandleRef = useRef<HTMLDivElement | null>(null)

        const dragX = useMotionValue(0)
        const springX = useSpring(dragX, ANIMATION_CONFIG.spring)
        const dragProgress = useTransform(
            springX,
            [0, DRAG_CONSTRAINTS.right],
            [0, 1]
        )

        const handleSubmit = useCallback(() => {
            setStatus("loading")
            setTimeout(() => {
                setStatus("success")
                if (onSuccess) onSuccess()

                if (resetOnSuccess) {
                    setTimeout(() => {
                        setCompleted(false);
                        setStatus("idle");
                        dragX.set(0);
                    }, 600);
                }
            }, 600)
        }, [onSuccess, resetOnSuccess, dragX])

        const handleClick = useCallback(() => {
            if (completed || disabled) return
            setIsDragging(true)
            // Auto-animate the slide
            dragX.set(DRAG_CONSTRAINTS.right)
            setTimeout(() => {
                setCompleted(true)
                handleSubmit()
            }, 600)
        }, [completed, disabled, dragX, handleSubmit])

        const adjustedWidth = useTransform(springX, (x) => x + 48)

        return (
            <motion.div
                animate={completed ? BUTTON_STATES.completed : BUTTON_STATES.initial}
                transition={ANIMATION_CONFIG.spring}
                className={cn(
                    "relative flex h-12 flex-shrink-0 items-center justify-center rounded-full bg-[#E8D5C4] overflow-hidden cursor-pointer hover:shadow-lg transition-all",
                    disabled && "opacity-50 cursor-not-allowed",
                    className
                )}
                onClick={handleClick}
            >
                {!completed && (
                    <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold text-[#8B6F5E] pointer-events-none pl-6 select-none">
                        {children || "Click to slide"}
                    </span>
                )}

                {!completed && (
                    <motion.div
                        style={{
                            width: adjustedWidth,
                        }}
                        className="absolute inset-y-0 left-0 z-0 rounded-full bg-[#A0522D] opacity-20 pointer-events-none"
                    />
                )}
                <AnimatePresence key={Math.random().toString(36).slice(2)}>
                    {!completed && (
                        <motion.div
                            ref={dragHandleRef}
                            style={{ x: springX }}
                            className="absolute left-0 z-10 flex items-center justify-start"
                        >
                            <Button
                                ref={ref}
                                disabled={disabled || status === "loading"}
                                type="button"
                                size="icon"
                                style={{ height: "48px", width: "48px" }}
                                className={cn(
                                    "rounded-full drop-shadow-md bg-[#3B2314] hover:bg-[#5C3A21] text-white flex-shrink-0 transition-transform",
                                    isDragging && "scale-105"
                                )}
                                {...props}
                            >
                                <ArrowRight className="size-5" />
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>

                <AnimatePresence key={Math.random().toString(36).slice(2)}>
                    {completed && (
                        <motion.div
                            className="absolute inset-0 flex items-center justify-center bg-[#F5EDE4]"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                        >
                            <Button
                                ref={ref}
                                disabled={true}
                                className="size-full rounded-full transition-all duration-300 bg-transparent hover:bg-transparent shadow-none"
                            >
                                <AnimatePresence key={Math.random().toString(36).slice(2)} mode="wait">
                                    <StatusIcon status={status} />
                                </AnimatePresence>
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        )
    }
)

SlideButton.displayName = "SlideButton"
